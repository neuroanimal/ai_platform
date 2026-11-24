"""Unit tests of the agent-with-RAG benchmark (scripted model, hashing embedder)."""

import json

import pytest

from ai_platform.backend.domain_layer.business_logic.agent_benchmark.agent_rag_tasks import (
    AgentRagTask,
    get_agent_rag_tasks,
)
from ai_platform.backend.service_layer.macro.agent_benchmark.agent_rag_evaluator import (
    VARIANTS,
    evaluate_agent_rag,
)
from ai_platform.backend.ui_layer.cli import agent_rag_benchmark_cli
from ai_platform.common.llm.chat_result import ChatResult
from ai_platform.common.rag.embedder import HashingEmbedder

ANSWERS = {t.question: t.expected.split("|")[0] for t in get_agent_rag_tasks()}


class ScriptedAgentLLM:
    """RAG: answers at once. Agent (json protocol): one search, then the answer."""

    calls = 0

    def __init__(self, model):
        self.model = model

    def chat_completion(self, messages, **_):
        """Answer by question; in agent mode search first."""
        ScriptedAgentLLM.calls += 1
        question = next(m["content"] for m in messages if m["role"] == "user")
        agent = any("search_documents" in m["content"] for m in messages
                    if m["role"] == "system" and "PASSAGES" not in m["content"])
        searched = any(m["content"].startswith("Tool ") for m in messages if m["role"] == "user")
        if agent and not searched:
            return ChatResult(text=json.dumps({"tool": "search_documents",
                                               "arguments": {"query": question}}),
                              model=self.model)
        text = f"Odpowiedź: {ANSWERS[question]}"
        return ChatResult(text=json.dumps({"answer": text}) if agent else text, model=self.model)

    def shutdown(self):
        """Nothing to release."""


def test_tasks_are_consistent():
    tasks = get_agent_rag_tasks()
    assert len(tasks) == 11 and len({t.task_id for t in tasks}) == 11
    with pytest.raises(ValueError):
        AgentRagTask("x", "lookup", "pl", "q", "1", "numeric", [])
    with pytest.raises(ValueError):
        get_agent_rag_tasks("nope")


def test_evaluate_three_variants(tmp_path):
    report = evaluate_agent_rag(["m"], ScriptedAgentLLM, HashingEmbedder(), agent_mode="json")
    assert [s["variant"] for s in report["summary"]] == list(VARIANTS)
    rag, search, search_calc, first = report["summary"]
    assert rag["correct"] == search["correct"] == search_calc["correct"] == first["correct"] == 11
    assert rag["mean_model_calls"] == 1 and search["mean_model_calls"] == 2
    assert first["mean_model_calls"] == 1  # passages preloaded: answered without a search
    assert rag["correct_lookup_calc"] == "5/5" and rag["correct_general"] == "2/2"
    for row in report["results"]:
        assert (row["retrieval_hit"] is None) == (row["kind"] == "general")
        assert row["tools_used"] == ([] if row["variant"] in ("rag", "search_first_calc")
                                     else ["search_documents"])
    paths = agent_rag_benchmark_cli.write_reports(report, tmp_path / "r.json", "T")
    assert all(p.exists() for p in paths)
    assert "Lookup + calc" in paths[1].read_text(encoding="utf-8")


def test_unknown_variant_and_prompt():
    with pytest.raises(ValueError):
        evaluate_agent_rag(["m"], ScriptedAgentLLM, HashingEmbedder(), variants=["magic"])
    with pytest.raises(ValueError):
        evaluate_agent_rag(["m"], ScriptedAgentLLM, HashingEmbedder(), prompt="v9")


def test_min_score_drops_passages_and_prompt_versions():
    seen = []

    class Recorder(ScriptedAgentLLM):
        """Keeps the system prompts."""

        def chat_completion(self, messages, **kwargs):
            """Record, then answer as the scripted model."""
            seen.append(messages[0]["content"])
            return super().chat_completion(messages, **kwargs)

    evaluate_agent_rag(["m"], Recorder, HashingEmbedder(), variants=["rag"], min_score=1.01)
    assert all(s.startswith("No document matched") for s in seen)
    seen.clear()
    evaluate_agent_rag(["m"], Recorder, HashingEmbedder(), variants=["rag"], prompt="v1")
    assert all(s.startswith("Answer using the numbered passages") for s in seen)


def test_rescreen_uses_current_task_definitions(tmp_path):
    report = evaluate_agent_rag(["m"], ScriptedAgentLLM, HashingEmbedder(), variants=["rag"])
    founder = next(r for r in report["results"] if r["task_id"] == "lookup_founder_en")
    founder["answer"], founder["expected"] = "Założyła ją Halinę Wrzos.", "Halina Wrzos"
    founder["screening"] = "manual_review"
    path = tmp_path / "old.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    assert agent_rag_benchmark_cli.main(["--rescreen", str(path),
                                         "--output", str(tmp_path / "new.json")]) == 0
    new = json.loads((tmp_path / "new.json").read_text(encoding="utf-8"))
    row = next(r for r in new["results"] if r["task_id"] == "lookup_founder_en")
    assert row["screening"].startswith("candidate_correct") and "rescreened_at_utc" in new
