"""
When does the tool loop help RAG? Plain RAG vs. agent with search vs. agent
with search and calculator.

Every task of an ``agent_rag`` task set is answered by every model in three
variants:

- ``rag``: the top-k passages for the question go into the system prompt
  (``chat_service.RAG_SYSTEM``, the same prompt as the browser chat) - one call;
- ``agent_search``: ``ToolAgent`` with only ``search_documents`` - the model
  decides whether and what to search;
- ``agent_search_calc``: the same plus ``calculator``.

Per run: the answer's screening (``answer_screening``, the rule-based check),
whether the documents holding the facts were found (``retrieval_hit``: in the
retrieved passages for ``rag``, in the results of the agent's searches
otherwise; ``None`` for general-knowledge tasks), tools used, model calls and
seconds. The summary is per model and variant, split by task kind (lookup,
lookup_calc, general), so the cost of the loop can be set against its gain.

The LLM factory and the embedder are injected, as in the other benchmarks.
"""

import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Sequence

from ai_platform.backend.domain_layer.business_logic.agent_benchmark.agent_rag_tasks import (
    KINDS,
    AgentRagTask,
    get_agent_rag_tasks,
)
from ai_platform.backend.domain_layer.business_logic.rag_benchmark.qa_sets import get_qa_set
from ai_platform.backend.service_layer.macro.chat.chat_service import RAG_SYSTEM
from ai_platform.common.agent.agent_loop import ToolAgent
from ai_platform.common.agent.builtin_tools import CALCULATOR, rag_search_tool
from ai_platform.common.agent.tool import ToolRegistry
from ai_platform.common.evaluation.answer_screening import assess_answer
from ai_platform.common.llm.llm_exception import LLMError
from ai_platform.common.rag.native_rag_adapter import NativeRAGAdapter

REPORT_SCHEMA = "ai_platform.agent_rag_benchmark.report/1"
VARIANTS = ("rag", "agent_search", "agent_search_calc")
AGENT_SYSTEM = ("You are a careful assistant. Use search_documents for facts about companies; "
                "{calc}Answer briefly in the language of the question.")
CALC_HINT = "use the calculator for every calculation. "


def build_index(embedder, corpus: str = "bilingual_qa") -> NativeRAGAdapter:
    """RAG index over the corpus (one chunk per document)."""
    rag = NativeRAGAdapter()
    rag.initialize({"embedder": embedder, "chunk_size": 4000, "chunk_overlap": 0})
    rag.ingest([{"id": d.doc_id, "text": d.text} for d in get_qa_set(corpus).documents])
    return rag


def _hit(task: AgentRagTask, found_ids: Sequence[str]):
    """All relevant documents among ``found_ids``; None when the task needs none."""
    if not task.relevant:
        return None
    return all(doc in found_ids for doc in task.relevant)


def run_rag(llm, rag, task: AgentRagTask, top_k: int) -> Dict[str, Any]:
    """Plain RAG: retrieve, one model call."""
    start = time.perf_counter()
    sources = rag.retrieve(task.question, top_k)
    context = "\n\n".join(f"[{n}] ({s.get('document_id')}) {s['text']}"
                          for n, s in enumerate(sources, start=1))
    try:
        answer = llm.chat_completion(
            [{"role": "system", "content": RAG_SYSTEM.format(context=context)},
             {"role": "user", "content": task.question}]).text
        stop = "answered"
    except LLMError as exc:
        answer, stop = "", f"llm_error: {type(exc).__name__}: {exc}"
    return {"answer": answer, "stop_reason": stop, "tools_used": [], "model_calls": 1,
            "retrieval_hit": _hit(task, [s.get("document_id") for s in sources]),
            "retrieved": [s.get("document_id") for s in sources],
            "elapsed_seconds": round(time.perf_counter() - start, 2), "trace": []}


def run_agent(llm, rag, task: AgentRagTask, *, calculator: bool, top_k: int,  # pylint: disable=too-many-arguments
              mode: str, max_steps: int) -> Dict[str, Any]:
    """Agent with search (and calculator)."""
    tools = [rag_search_tool(rag, top_k=top_k)] + ([CALCULATOR] if calculator else [])
    agent = ToolAgent(llm, ToolRegistry(tools), mode=mode, max_steps=max_steps,
                      system_prompt=AGENT_SYSTEM.format(calc=CALC_HINT if calculator else ""))
    run = agent.run(task.question)
    search_results = " ".join(c["result"] for s in run.steps for c in s.tool_calls
                              if c["name"] == "search_documents" and c["ok"])
    return {"answer": run.answer or "", "stop_reason": run.stop_reason,
            "tools_used": run.tools_used, "model_calls": len(run.steps),
            "retrieval_hit": _hit(task, [d for d in task.relevant if d in search_results]),
            "retrieved": [], "elapsed_seconds": round(run.elapsed_seconds, 2),
            "trace": run.to_dict()["steps"]}


def _screen(task: AgentRagTask, answer: str, stop_reason: str) -> str:
    return assess_answer({
        "test_id": task.task_id, "checker": task.checker, "language": task.language,
        "expected": task.expected, "answer": answer, "finish_reason": "stop",
        "status": "PASS" if answer else "FAIL", "error": stop_reason})["status"]


def rescreen(report: Dict[str, Any]) -> Dict[str, Any]:
    """The report screened again with the current task definitions (no model calls)."""
    tasks = {t.task_id: t for t in get_agent_rag_tasks(report.get("task_set", "agent_rag"))}
    rows = []
    for row in report["results"]:
        task = tasks[row["task_id"]]
        rows.append({**row, "expected": task.expected,
                     "screening": _screen(task, row["answer"], row["stop_reason"])})
    return {**report, "results": rows, "summary": summarize(rows),
            "rescreened_at_utc": datetime.now(timezone.utc).isoformat()}


def _run_one(llm, rag, task: AgentRagTask, variant: str, *, top_k: int,  # pylint: disable=too-many-arguments
             mode: str, max_steps: int) -> Dict[str, Any]:
    """One task in one variant, screened."""
    if variant == "rag":
        result = run_rag(llm, rag, task, top_k)
    else:
        result = run_agent(llm, rag, task, top_k=top_k, mode=mode, max_steps=max_steps,
                           calculator=variant == "agent_search_calc")
    return {"variant": variant, "task_id": task.task_id, "kind": task.kind,
            "language": task.language, "question": task.question, "expected": task.expected,
            "screening": _screen(task, result["answer"], result["stop_reason"]), **result}


def _correct(row: Dict[str, Any]) -> bool:
    return row["screening"].startswith("candidate_correct")


def summarize(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Per model and variant: answers right by kind, retrieval, cost."""
    groups: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["model"], row["variant"])].append(row)
    summary = []
    for (model, variant), items in sorted(groups.items(),
                                          key=lambda g: (g[0][0], VARIANTS.index(g[0][1]))):
        entry = {"model": model, "variant": variant, "tasks": len(items),
                 "correct": sum(_correct(r) for r in items)}
        for kind in KINDS:
            of_kind = [r for r in items if r["kind"] == kind]
            entry[f"correct_{kind}"] = f"{sum(_correct(r) for r in of_kind)}/{len(of_kind)}"
        hits = [r["retrieval_hit"] for r in items if r["retrieval_hit"] is not None]
        entry["retrieval_hit"] = f"{sum(hits)}/{len(hits)}"
        entry["mean_model_calls"] = round(sum(r["model_calls"] for r in items) / len(items), 2)
        entry["mean_seconds"] = round(sum(r["elapsed_seconds"] for r in items) / len(items), 1)
        entry["not_answered"] = sum(r["stop_reason"] != "answered" for r in items)
        summary.append(entry)
    return summary


def evaluate_agent_rag(models: Sequence[str],  # pylint: disable=too-many-arguments,too-many-locals
                       llm_factory: Callable[[str], Any], embedder, *,
                       variants: Sequence[str] = VARIANTS, task_set: str = "agent_rag",
                       top_k: int = 3, agent_mode: str = "auto", max_steps: int = 5,
                       progress: Callable[[str], None] = lambda m: None) -> Dict[str, Any]:
    """Answer every task with every model in every variant."""
    unknown = set(variants) - set(VARIANTS)
    if unknown:
        raise ValueError(f"unknown variants {sorted(unknown)}; choose from {VARIANTS}")
    tasks = get_agent_rag_tasks(task_set)
    rag = build_index(embedder)
    rows: List[Dict[str, Any]] = []
    try:
        for model in models:
            llm = llm_factory(model)
            try:
                for variant in variants:
                    progress(f"model {model} variant {variant}")
                    for task in tasks:
                        row = _run_one(llm, rag, task, variant, top_k=top_k, mode=agent_mode,
                                       max_steps=max_steps)
                        rows.append({"model": model, **row})
                        progress(f"  {task.task_id}: {row['tools_used']} -> "
                                 f"{row['screening']} ({row['elapsed_seconds']} s)")
            finally:
                llm.shutdown()
    finally:
        rag.shutdown()
    return {"schema": REPORT_SCHEMA, "task_set": task_set,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "models": list(models), "variants": list(variants), "top_k": top_k,
            "agent_mode": agent_mode, "max_steps": max_steps,
            "summary": summarize(rows), "results": rows}
