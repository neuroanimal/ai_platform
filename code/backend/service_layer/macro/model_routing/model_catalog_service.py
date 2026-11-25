"""
Model catalog: the installed models with what our benchmarks measured about them.

``build_profiles(facts, reports)`` joins:

- facts from the model server (``OllamaAdapter.model_facts``: size,
  capabilities, context, loaded or not) - the list of models IS the server's
  list, so a deleted model disappears and a new one appears as unmeasured;
- scores from benchmark reports found on disk (``find_reports``), newest
  report first per kind and model:
  - bilingual reasoning (``*_screening*.json`` of the LLM benchmark):
    ``chat:pl`` / ``chat:en`` = share of answers the screening marked correct
    (``candidate_correct*``; a human verdict, where given, wins), and the
    median seconds per answer;
  - agent-RAG (``agent_rag*.json``): ``documents`` = plain RAG variant
    correct / tasks; ``tools`` falls back to the best agent variant;
  - tool use (``tool_use*.json``): ``tools`` = best mode both_ok / tasks.

Only reports of the time-budget protocol (``max_seconds`` set, from
2026-11-25) are used for chat scores when one exists for the model: older
runs gave every model 768 tokens, which is not the same contest.

``ModelCatalogService`` caches the facts for a few seconds and the reports
until ``refresh``; ``decide`` routes one request.
"""

import json
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from ai_platform.backend.domain_layer.business_logic.model_routing.routing_policy import (
    ModelProfile,
    RouteDecision,
    RoutingPreferences,
    detect_language,
    route,
)

#: code/ -> repository root
REPO_ROOT = Path(__file__).resolve().parents[5]
REPORT_DIRS = (REPO_ROOT / "doc" / "report" / "benchmarks",
               REPO_ROOT / "config" / "test_env" / "results")
FACTS_CACHE_SECONDS = 10.0


def find_reports(directories: Iterable[Path] = REPORT_DIRS) -> List[Path]:
    """Benchmark report files, newest first (by modification time)."""
    found = []
    for directory in directories:
        if Path(directory).is_dir():
            found += [p for p in Path(directory).rglob("*.json")
                      if p.name.startswith(("llm_benchmark", "agent_rag", "tool_use"))]
    return sorted(set(found), key=lambda p: p.stat().st_mtime, reverse=True)


def _load(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _correct(row: Dict[str, Any]) -> bool:
    assessment = row.get("automatic_assessment", {}).get("answer_screening", {})
    human = assessment.get("human_verdict")
    if human:
        return human == "correct"
    return str(assessment.get("status", "")).startswith("candidate_correct")


def _screening_scores(data: Dict[str, Any]) -> Dict[Tuple[str, str], Tuple[float, float, bool]]:
    """(model, language) -> (share correct, median seconds, time-budget protocol)."""
    report = _load(Path(str(data.get("source_report") or data.get("source") or ""))) or {}
    budget = report.get("max_seconds") is not None
    groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in data.get("results", []):
        groups[(row.get("model"), row.get("language"))].append(row)
    scores = {}
    for key, rows in groups.items():
        times = [r["elapsed_seconds"] for r in rows if r.get("elapsed_seconds") is not None]
        scores[key] = (sum(_correct(r) for r in rows) / len(rows),
                       statistics.median(times) if times else 0.0, budget)
    return scores


def _ratio(entry: Dict[str, Any], numerator: str, denominator: str = "tasks") -> Optional[float]:
    total = entry.get(denominator)
    return entry.get(numerator, 0) / total if total else None


def collect_measurements(paths: Sequence[Path]) -> Dict[str, Dict[str, Any]]:  # pylint: disable=too-many-branches
    """model -> {"quality": {...}, "seconds": {...}, "sources": {...}}; newest report wins."""
    out: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"quality": {}, "seconds": {},
                                                          "sources": {}, "budget": {}})

    def put(model, key, quality, seconds, source, budget=True):  # pylint: disable=too-many-arguments,too-many-positional-arguments
        entry = out[model]
        if key in entry["quality"] and (entry["budget"].get(key) or not budget):
            return  # a newer report, or a time-budget one, already set it
        entry["quality"][key] = round(quality, 3)
        if seconds is not None:
            entry["seconds"][key] = round(seconds, 1)
        entry["sources"][key] = source
        entry["budget"][key] = budget

    for path in paths:
        data = _load(path)
        if not data:
            continue
        schema = str(data.get("schema") or "")
        if "screening" in path.name and isinstance(data.get("results"), list):
            for (model, language), (share, seconds, budget) in \
                    _screening_scores(data).items():
                put(model, f"chat:{language}", share, seconds, path.name, budget)
        elif schema.startswith("ai_platform.agent_rag_benchmark"):
            for entry in data.get("summary", []):
                share = _ratio(entry, "correct")
                if share is None:
                    continue
                if entry.get("variant") == "rag":
                    put(entry["model"], "documents", share, entry.get("mean_seconds"),
                        path.name)
                elif "tools" not in out[entry["model"]]["sources"] or \
                        out[entry["model"]]["sources"]["tools"].startswith("agent_rag"):
                    best = out[entry["model"]]["quality"].get("tools", -1)
                    if share > best:
                        out[entry["model"]]["quality"]["tools"] = round(share, 3)
                        out[entry["model"]]["seconds"]["tools"] = entry.get("mean_seconds")
                        out[entry["model"]]["sources"]["tools"] = path.name
        elif schema.startswith("ai_platform.tool_use_benchmark"):
            best: Dict[str, float] = {}
            for entry in data.get("summary", []):
                share = _ratio(entry, "both_ok")
                if share is not None and share > best.get(entry["model"], -1):
                    best[entry["model"]] = share
            for model, share in best.items():
                if not str(out[model]["sources"].get("tools", "")).startswith("tool_use"):
                    out[model]["quality"]["tools"] = round(share, 3)
                    out[model]["sources"]["tools"] = path.name
    return dict(out)


def build_profiles(facts: Sequence[Dict[str, Any]],
                   measurements: Dict[str, Dict[str, Any]]) -> List[ModelProfile]:
    """One profile per installed model (facts) with its measurements."""
    profiles = []
    for fact in facts:
        name = fact["name"]
        # Reports name a model as it was asked for ("phi4-mini"), Ollama lists "phi4-mini:latest".
        measured = measurements.get(name) or measurements.get(name.removesuffix(":latest")) or {}
        profiles.append(ModelProfile(
            name=fact["name"], size_gb=float(fact.get("size_gb") or 0.0),
            capabilities=tuple(fact.get("capabilities") or ()),
            loaded=bool(fact.get("loaded")), context_trained=fact.get("context_trained"),
            quality=dict(measured.get("quality") or {}),
            seconds=dict(measured.get("seconds") or {}),
            sources=dict(measured.get("sources") or {})))
    return profiles


class ModelCatalogService:
    """Facts from the model server + measurements from reports; routes requests."""

    def __init__(self, facts_source, report_dirs: Iterable[Path] = REPORT_DIRS,
                 preferences: Optional[RoutingPreferences] = None) -> None:
        """``facts_source()`` returns ``model_facts()``-style dicts (e.g. an OllamaAdapter's)."""
        self.facts_source = facts_source
        self.report_dirs = tuple(report_dirs)
        self.preferences = preferences or RoutingPreferences()
        self._measurements: Optional[Dict[str, Dict[str, Any]]] = None
        self._facts: Tuple[float, List[Dict[str, Any]]] = (0.0, [])

    def refresh(self) -> None:
        """Read the reports again (after a new benchmark run)."""
        self._measurements = collect_measurements(find_reports(self.report_dirs))

    def profiles(self) -> List[ModelProfile]:
        """Current profiles (facts cached ``FACTS_CACHE_SECONDS``)."""
        if self._measurements is None:
            self.refresh()
        stamp, facts = self._facts
        if time.monotonic() - stamp > FACTS_CACHE_SECONDS:
            facts = list(self.facts_source())
            self._facts = (time.monotonic(), facts)
        return build_profiles(facts, self._measurements or {})

    def decide(self, task: str, text: str, language: Optional[str] = None) -> RouteDecision:
        """Route one request; the language is detected from ``text`` unless given."""
        return route(self.profiles(), task, language or detect_language(text), self.preferences)
