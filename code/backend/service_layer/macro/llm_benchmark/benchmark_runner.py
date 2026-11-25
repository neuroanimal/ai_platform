"""
Run a benchmark task set against one or more models.

Integrated from ``config/test_env/test_30_bilingual_quality_v3.py``. The
service depends only on:

- the domain task model (``domain_layer.business_logic.llm_benchmark``), and
- an *LLM factory*: ``factory(model_name) -> adapter`` returning an
  initialized adapter with ``chat_completion(messages, **kw) -> ChatResult``
  and ``shutdown()`` (any adapter from ``common.llm``).

so the transport (LocalAI, Ollama, a hosted API) is chosen by the caller.

Per model: one warm-up request (its time includes model loading and is
reported separately), then ``repeats`` x tasks x languages measured
requests. A request that fails is recorded with ``status: FAIL`` and
``error_type``; it does not stop the run. ``status: PASS`` means only "an
answer came back" - correctness is the screening step's business.

The report is a plain dict (JSON-serializable); writing it is the caller's
job (the CLI in ``ui_layer``).
"""

import statistics
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence

from ai_platform.backend.domain_layer.business_logic.llm_benchmark.task_model import TaskSet
from ai_platform.common.llm.generation_guard import LOOP_REPEATS, guarded_chat
from ai_platform.common.llm.llm_exception import LLMError, LLMResponseError

REPORT_SCHEMA = "ai_platform.llm_benchmark.report/1"
WARMUP_PROMPT = "Odpowiedz jednym słowem: OK."

LLMFactory = Callable[[str], Any]
Progress = Callable[[str], None]


class LLMBenchmarkRunner:  # pylint: disable=too-few-public-methods
    """Runs task sets against models created by an LLM factory."""

    def __init__(self, llm_factory: LLMFactory, progress: Optional[Progress] = None,  # pylint: disable=too-many-arguments
                 clock: Callable[[], float] = time.perf_counter, *,
                 max_seconds: Optional[float] = None,
                 loop_repeats: Optional[int] = None) -> None:
        """``max_seconds`` and/or ``loop_repeats`` switch to guarded, streamed calls
        (``generation_guard``): every answer gets the same wall-clock budget and
        a looping answer is stopped; without them each answer is one plain call
        limited by the adapter's max_tokens (the behaviour of the first runs)."""
        self.llm_factory = llm_factory
        self.progress = progress or (lambda message: None)
        self.clock = clock
        self.max_seconds = max_seconds
        self.loop_repeats = loop_repeats

    def run(self, task_set: TaskSet, models: Sequence[str], *,  # pylint: disable=too-many-arguments,too-many-locals
            languages: Optional[Sequence[str]] = None, repeats: int = 3,
            warmup: bool = True, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run the benchmark; return the report dict."""
        if repeats < 1:
            raise ValueError("repeats must be >= 1")
        if not models:
            raise ValueError("at least one model is needed")
        languages = task_set.select(languages)
        results: List[Dict[str, Any]] = []
        warmups: Dict[str, Dict[str, Any]] = {}
        started = datetime.now(timezone.utc).isoformat()

        for model in models:
            self.progress(f"model {model}")
            llm = self.llm_factory(model)
            try:
                warmups[model] = self._warm_up(llm) if warmup else {"status": "SKIPPED"}
                if warmups[model]["status"] == "FAIL":
                    self.progress(f"  warm-up failed: {warmups[model]['error']}")
                    continue
                for run_index in range(repeats):
                    for task in task_set.tasks:
                        for language in languages:
                            record = self._ask(llm, model, task, language, run_index)
                            results.append(record)
                            self.progress(f"  {task.task_id} [{language}] run {run_index}: "
                                          f"{record['status']} {record.get('elapsed_seconds')}")
            finally:
                llm.shutdown()

        return {
            "schema": REPORT_SCHEMA,
            "task_set": task_set.name,
            "task_set_version": task_set.version,
            "created_at_utc": started,
            "models": list(models),
            "languages": languages,
            "repeats": repeats,
            "warmup": warmups,
            "status_semantics": "PASS = an answer came back; correctness is screened separately",
            "max_seconds": self.max_seconds, "loop_repeats": self.loop_repeats,
            **(metadata or {}),
            "summary": summarize(results, models, languages, len(task_set.tasks) * repeats),
            "results": results,
        }

    def _warm_up(self, llm) -> Dict[str, Any]:
        try:
            result = llm.chat_completion([{"role": "user", "content": WARMUP_PROMPT}],
                                         max_tokens=8, temperature=0)
            return {"status": "PASS", "load_and_warmup_seconds": round(result.elapsed_seconds, 3)}
        except LLMResponseError as exc:
            # A reasoning model spends the 8 warm-up tokens thinking: loaded, but no answer.
            if "empty answer" in str(exc):
                return {"status": "PASS", "note": "empty warm-up answer (reasoning model?)"}
            return {"status": "FAIL", "error_type": type(exc).__name__, "error": str(exc)}
        except LLMError as exc:
            return {"status": "FAIL", "error_type": type(exc).__name__, "error": str(exc)}

    def _ask(self, llm, model: str, task, language: str, run_index: int) -> Dict[str, Any]:
        localized = task.prompt(language)
        base = {"model": model, "test_id": task.task_id, "checker": task.checker,
                "category": task.category, "language": language, "run_index": run_index,
                "prompt": localized.prompt, "expected": localized.expected,
                "rejected": list(localized.rejected)}
        messages = [{"role": "user", "content": localized.prompt}]
        sent = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        try:
            guarded = self.max_seconds is not None or self.loop_repeats is not None
            if guarded and hasattr(llm, "stream_chat"):
                result = guarded_chat(llm, messages, max_seconds=self.max_seconds,
                                      loop_repeats=self.loop_repeats or LOOP_REPEATS)
            else:
                result = llm.chat_completion(messages)
        except LLMError as exc:
            return {**base, "status": "FAIL", "error_type": type(exc).__name__, "error": str(exc),
                    "timing": {"request_sent_utc": sent,
                               "finished_utc": datetime.now(timezone.utc).isoformat(
                                   timespec="milliseconds")}}
        timing = (result.metrics or {}).get("timing") or {
            "request_sent_utc": sent,
            "finished_utc": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "elapsed_seconds": round(result.elapsed_seconds, 3)}
        record = {**base, "status": "PASS" if result.text.strip() else "FAIL",
                  "answer": result.text, "elapsed_seconds": round(result.elapsed_seconds, 3),
                  "usage": result.usage, "finish_reason": result.finish_reason,
                  "timing": timing}
        if result.reasoning:
            record["reasoning"] = result.reasoning
        if result.finish_reason == "loop":
            record["loop_unit"] = timing.get("loop_unit")
        if not result.text.strip():
            record["error"] = {
                "loop": f"stopped: the model looped on {timing.get('loop_unit')!r}",
                "time_limit": f"stopped: time limit of {self.max_seconds} s before an answer",
            }.get(result.finish_reason, "empty answer" + (" (only reasoning)"
                                                         if result.reasoning else ""))
        return record


def summarize(results: List[Dict[str, Any]], models: Sequence[str],
              languages: Sequence[str], expected_per_cell: int) -> Dict[str, Any]:
    """Per model/language: executions, median/max latency, truncations."""
    summary = {}
    for model in models:
        for language in languages:
            rows = [r for r in results if r["model"] == model and r["language"] == language]
            times = [r["elapsed_seconds"] for r in rows if r["status"] == "PASS"]
            summary[f"{model} [{language.upper()}]"] = {
                "technical_pass": len(times),
                "expected_executions": expected_per_cell,
                "median_seconds": round(statistics.median(times), 3) if times else None,
                "max_seconds": max(times) if times else None,
                "truncated": sum(r.get("finish_reason") == "length" for r in rows),
                "time_limited": sum(r.get("finish_reason") == "time_limit" for r in rows),
                "looped": sum(r.get("finish_reason") == "loop" for r in rows),
            }
    return summary


#: Settings that must be equal for two reports to be comparable.
COMPARABLE_KEYS = ("schema", "task_set", "task_set_version", "languages", "repeats",
                   "temperature", "max_tokens", "provider", "max_seconds")


def merge_reports(reports: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Combine reports of separate runs into one (e.g. models run on different nights).

    Refuses reports whose settings differ (``COMPARABLE_KEYS``) - their numbers
    would not be comparable - or that measure the same model twice.
    """
    if not reports:
        raise ValueError("nothing to merge")
    first = reports[0]
    for other in reports[1:]:
        differing = [k for k in COMPARABLE_KEYS if other.get(k) != first.get(k)]
        if differing:
            raise ValueError(f"reports are not comparable, they differ in {differing}")
    models: List[str] = []
    for report in reports:
        duplicated = set(models) & set(report["models"])
        if duplicated:
            raise ValueError(f"model(s) measured in more than one report: {sorted(duplicated)}")
        models.extend(report["models"])
    results = [row for report in reports for row in report["results"]]
    warmups = {k: v for report in reports for k, v in report.get("warmup", {}).items()}
    expected = len(first["results"]) // max(1, len(first["models"]) * len(first["languages"]))
    return {**first, "models": models, "warmup": warmups,
            "merged_from": [r.get("created_at_utc") for r in reports],
            "summary": summarize(results, models, first["languages"], expected),
            "results": results}
