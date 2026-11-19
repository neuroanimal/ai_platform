"""
Measure tool use of LLMs with the platform's agent loop.

For every model and mode (``auto``, ``native``, ``json``) each task of a
tool task set is run through ``ToolAgent`` with the built-in tools plus a
``search_documents`` tool over the ``bilingual_qa`` corpus. Per run:

- ``tool_choice``: the expected tools were used (an expected entry "a|b"
  accepts either), and for no-tool tasks no tool was used;
- ``valid_calls``: share of tool calls whose arguments passed validation
  and ran without error;
- ``answer``: screening of the final answer (``answer_screening``);
- ``steps`` and ``stop_reason`` from the loop's trace (kept in full).

The LLM factory and the embedder are injected, as in the other benchmarks.
"""

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Sequence

from ai_platform.backend.domain_layer.business_logic.agent_benchmark.tool_tasks import (
    ToolTask,
    get_tool_tasks,
)
from ai_platform.backend.domain_layer.business_logic.rag_benchmark.qa_sets import get_qa_set
from ai_platform.common.agent.agent_loop import ToolAgent
from ai_platform.common.agent.builtin_tools import default_tools, rag_search_tool
from ai_platform.common.agent.tool import ToolRegistry
from ai_platform.common.evaluation.answer_screening import assess_answer
from ai_platform.common.rag.native_rag_adapter import NativeRAGAdapter

REPORT_SCHEMA = "ai_platform.tool_use_benchmark.report/1"
SYSTEM_PROMPT = ("You are a careful assistant. Use the calculator for every calculation, "
                 "convert_units for unit conversions and search_documents for facts about "
                 "companies. Answer briefly in the language of the question.")

__all__ = ["evaluate_tool_use", "get_tool_tasks", "REPORT_SCHEMA"]


def tool_choice_ok(task: ToolTask, used: List[str]) -> bool:
    """Were the expected tools used (and none for a no-tool task)?"""
    if not task.expected_tools:
        return not used
    return all(any(name in used for name in entry.split("|")) for entry in task.expected_tools)


def build_registry(embedder) -> ToolRegistry:
    """Built-in tools plus search over the bilingual_qa corpus."""
    rag = NativeRAGAdapter()
    rag.initialize({"embedder": embedder, "chunk_size": 4000, "chunk_overlap": 0})
    rag.ingest([{"id": d.doc_id, "text": d.text} for d in get_qa_set("bilingual_qa").documents])
    return ToolRegistry(default_tools() + [rag_search_tool(rag)])


def _summarize(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["model"], row["mode"])].append(row)
    summary = []
    for (model, mode), items in sorted(groups.items()):
        calls = sum(r["tool_calls"] for r in items)
        summary.append({
            "model": model, "mode": mode, "tasks": len(items),
            "tool_choice_ok": sum(r["tool_choice_ok"] for r in items),
            "answer_correct": sum(r["screening"].startswith("candidate_correct") for r in items),
            "both_ok": sum(r["tool_choice_ok"] and r["screening"].startswith("candidate_correct")
                           for r in items),
            "valid_call_rate": round(sum(r["valid_calls"] for r in items) / calls, 3)
            if calls else None,
            "mean_steps": round(sum(r["steps"] for r in items) / len(items), 2),
            "errors": sum(not r["stop_reason"] == "answered" for r in items),
        })
    return summary


def evaluate_tool_use(models: Sequence[str],  # pylint: disable=too-many-arguments,too-many-locals
                      llm_factory: Callable[[str], Any], embedder, *,
                      modes: Sequence[str] = ("auto",), task_set: str = "tool_use",
                      max_steps: int = 5,
                      progress: Callable[[str], None] = lambda m: None) -> Dict[str, Any]:
    """Run every task for every model and mode."""
    tasks = get_tool_tasks(task_set)
    registry = build_registry(embedder)
    rows: List[Dict[str, Any]] = []
    for model in models:
        for mode in modes:
            progress(f"model {model} mode {mode}")
            llm = llm_factory(model)
            agent = ToolAgent(llm, registry, mode=mode, max_steps=max_steps,
                              system_prompt=SYSTEM_PROMPT)
            try:
                for task in tasks:
                    run = agent.run(task.question)
                    calls = [c for s in run.steps for c in s.tool_calls]
                    record = {"test_id": task.task_id, "checker": task.checker,
                              "language": task.language, "expected": task.expected,
                              "answer": run.answer or "", "finish_reason": "stop",
                              "status": "PASS" if run.answer else "FAIL",
                              "error": run.stop_reason}
                    screening = assess_answer(record)
                    rows.append({
                        "model": model, "mode": mode, "task_id": task.task_id,
                        "question": task.question, "expected": task.expected,
                        "expected_tools": list(task.expected_tools),
                        "tools_used": run.tools_used,
                        "tool_choice_ok": tool_choice_ok(task, run.tools_used),
                        "tool_calls": len(calls), "valid_calls": sum(c["ok"] for c in calls),
                        "steps": len(run.steps), "stop_reason": run.stop_reason,
                        "answer": run.answer, "screening": screening["status"],
                        "modes_used": sorted({s.mode for s in run.steps}),
                        "elapsed_seconds": round(run.elapsed_seconds, 2),
                        "trace": run.to_dict()["steps"]})
                    progress(f"  {task.task_id}: tools {run.tools_used} -> {screening['status']}")
            finally:
                llm.shutdown()
    return {"schema": REPORT_SCHEMA, "task_set": task_set,
            "created_at_utc": datetime.now(timezone.utc).isoformat(), "models": list(models),
            "modes": list(modes), "max_steps": max_steps, "summary": _summarize(rows),
            "results": rows}
