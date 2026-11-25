"""Unit tests of model routing: the policy, the catalog from reports, and "auto" in the chat."""

import json

import pytest

from ai_platform.backend.domain_layer.business_logic.model_routing.routing_policy import (
    ModelProfile,
    RoutingError,
    RoutingPreferences,
    detect_language,
    route,
)
from ai_platform.backend.service_layer.macro.model_routing.model_catalog_service import (
    ModelCatalogService,
    build_profiles,
    collect_measurements,
)


def _profiles():
    return [
        ModelProfile("small", 2.0, ("completion", "tools"), loaded=True,
                     quality={"chat:pl": 0.70, "chat:en": 0.85, "tools": 0.80},
                     seconds={"chat:pl": 3, "chat:en": 3, "tools": 5}),
        ModelProfile("bielik-big", 7.0, ("completion",), loaded=False,
                     quality={"chat:pl": 0.90, "chat:en": 0.88},
                     seconds={"chat:pl": 30, "chat:en": 25}),
        ModelProfile("unmeasured", 1.0, ("completion",)),
        ModelProfile("bge-m3", 1.2, ("embedding",), quality={"chat:pl": 1.0}),
    ]


def test_language_detection():
    assert detect_language("Ile wynosi 17 razy 23?") == "pl"
    assert detect_language("Zażółć gęślą jaźń") == "pl"
    assert detect_language("What is the capital of Australia?") == "en"


def test_route_trades_quality_against_time_and_loading():
    decision = route(_profiles(), "chat", "pl")
    # bielik: 0.90 - (30 + 7*3)/600 + 0.05 = 0.865; small: 0.70 - 3/600 = 0.695
    assert decision.model == "bielik-big" and "Polish model +0.05" in decision.reasons
    assert any("to load 7.0 GB" in r for r in decision.reasons)
    # English: no Polish bonus, 0.88 - 46/600 = 0.803 < 0.85 - 3/600 = 0.845
    assert route(_profiles(), "chat", "en").model == "small"
    impatient = RoutingPreferences(seconds_per_point=60)
    assert route(_profiles(), "chat", "pl", impatient).model == "small"
    assert route(_profiles(), "tools", "en").model == "small"
    assert all(c["model"] != "bge-m3" for c in route(_profiles(), "chat", "pl").ranking)


def test_route_preferences():
    assert route(_profiles(), "chat", "pl", RoutingPreferences(max_unloaded_gb=4)).model == \
        "small"
    assert route(_profiles(), "chat", "pl", RoutingPreferences(pinned={"chat": "unmeasured"})
                 ).model == "unmeasured"
    only_unmeasured = [_profiles()[2]]
    decision = route(only_unmeasured, "documents", "pl")
    assert decision.model == "unmeasured" and "without benchmark data" in decision.reasons[0]
    with pytest.raises(RoutingError):
        route(only_unmeasured, "documents", "pl", RoutingPreferences(allow_unmeasured=False))
    with pytest.raises(RoutingError):
        route(_profiles(), "dance", "pl")


def test_catalog_reads_reports_and_prefers_time_budget_runs(tmp_path):
    old_report = tmp_path / "old.json"
    old_report.write_text(json.dumps({"max_tokens": 768}), encoding="utf-8")
    new_report = tmp_path / "new.json"
    new_report.write_text(json.dumps({"max_seconds": 300}), encoding="utf-8")

    def screening(path, source, correct):
        rows = [{"model": "m", "language": "pl", "elapsed_seconds": 4.0,
                 "automatic_assessment": {"answer_screening": {
                     "status": "candidate_correct" if n < correct else "manual_review"}}}
                for n in range(4)]
        path.write_text(json.dumps({"source": str(source), "results": rows}), encoding="utf-8")
        return path

    budget = screening(tmp_path / "llm_benchmark_a_screening.json", new_report, 3)
    legacy = screening(tmp_path / "llm_benchmark_b_screening.json", old_report, 1)
    rag = tmp_path / "agent_rag_x.json"
    rag.write_text(json.dumps({"schema": "ai_platform.agent_rag_benchmark.report/1", "summary": [
        {"model": "m", "variant": "rag", "tasks": 11, "correct": 10, "mean_seconds": 6.0},
        {"model": "m", "variant": "agent_search", "tasks": 11, "correct": 7}]}),
        encoding="utf-8")
    measured = collect_measurements([legacy, budget, rag])  # legacy listed first = newer
    assert measured["m"]["quality"]["chat:pl"] == 0.75      # the time-budget run wins
    assert measured["m"]["quality"]["documents"] == pytest.approx(0.909, abs=1e-3)
    assert measured["m"]["quality"]["tools"] == pytest.approx(0.636, abs=1e-3)
    profiles = build_profiles([{"name": "m:latest", "size_gb": 1, "capabilities": ["completion"],
                                "loaded": True}], measured)
    assert profiles[0].quality["chat:pl"] == 0.75           # "m" in reports = "m:latest"
    service = ModelCatalogService(lambda: [{"name": "m", "size_gb": 1, "loaded": True,
                                            "capabilities": ["completion"]}],
                                  report_dirs=[tmp_path])
    assert service.decide("documents", "Ile ciężarówek?").model == "m"


def test_chat_auto_model_emits_route():
    from ai_platform.backend.service_layer.macro.chat.chat_service import (  # pylint: disable=import-outside-toplevel
        ChatService,
        Provider,
    )
    from ai_platform.common.llm.chat_result import StreamChunk  # pylint: disable=import-outside-toplevel

    class Fake:
        """Minimal local model server."""
        def initialize(self, config):
            """Remember the model."""
            self.model = config["model"]  # pylint: disable=attribute-defined-outside-init

        @staticmethod
        def list_models():
            """Two chat models."""
            return ["a", "b"]

        @staticmethod
        def stream_chat(messages, **_):
            """One chunk."""
            assert messages
            yield StreamChunk("ok", "stop")

    class Router:  # pylint: disable=too-few-public-methods
        """Always picks b."""
        @staticmethod
        def decide(task, text):
            """Decision for b."""
            return route([ModelProfile("b", 1, ("completion",), loaded=True,
                                       quality={"chat:pl": 0.9})], task, detect_language(text))

    service = ChatService(providers=[Provider("ollama", Fake, "http://x")], embedder="hashing",
                          router=Router())
    assert service.list_models()[0]["id"] == "auto"
    events = list(service.answer({"model": "auto",
                                  "messages": [{"role": "user", "content": "Cześć, co słychać?"}]}))
    assert events[0]["type"] == "route" and events[0]["model"] == "ollama:b"
    assert events[0]["language"] == "pl" and events[-1]["type"] == "done"
