"""
Evaluate RAG question answering: closed-book vs. retrieval-augmented.

For each model the QA set is answered twice:

- ``closed_book``: the question alone;
- ``rag``: the top-k documents retrieved by the platform's RAG pipeline
  (``NativeRAGAdapter`` with the chosen embedder) are put into the prompt.

Answers are screened with the item's checker; retrieval is scored with hit@k
against the item's relevant document. Splitting by ``fictional`` separates
"RAG supplies facts the model cannot know" from "context on general
knowledge". The prompt is written in the question's language.

Dependencies are injected: ``llm_factory(model)`` returns an initialized LLM
adapter (``chat_completion``/``shutdown``), ``embedder`` any Embedder.
"""

import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Sequence

from ai_platform.backend.domain_layer.business_logic.rag_benchmark.qa_sets import (
    QASet,
    get_qa_set,
    list_qa_sets,
)
from ai_platform.common.evaluation.answer_screening import assess_answer
from ai_platform.common.evaluation.retrieval_metrics import hit_at_k
from ai_platform.common.llm.llm_exception import LLMError
from ai_platform.common.rag.native_rag_adapter import NativeRAGAdapter

REPORT_SCHEMA = "ai_platform.rag_qa_benchmark.report/1"
MODES = ("closed_book", "rag")

PROMPTS = {
    "pl": {"closed_book": "Odpowiedz krótko na pytanie.\n\nPytanie: {question}\nOdpowiedź:",
           "rag": ("Odpowiedz krótko na pytanie, korzystając wyłącznie z poniższego kontekstu. "
                   "Jeśli kontekst nie zawiera odpowiedzi, napisz, że nie wiesz.\n\n"
                   "Kontekst:\n{context}\n\nPytanie: {question}\nOdpowiedź:")},
    "en": {"closed_book": "Answer the question briefly.\n\nQuestion: {question}\nAnswer:",
           "rag": ("Answer the question briefly, using only the context below. If the "
                   "context does not contain the answer, say that you do not know.\n\n"
                   "Context:\n{context}\n\nQuestion: {question}\nAnswer:")},
}

__all__ = ["evaluate_qa", "get_qa_set", "list_qa_sets", "REPORT_SCHEMA", "MODES"]


def _index(qa_set: QASet, embedder, top_k: int) -> NativeRAGAdapter:
    rag = NativeRAGAdapter()
    rag.initialize({"embedder": embedder, "top_k": top_k, "chunk_size": 4000,
                    "chunk_overlap": 0})
    rag.ingest([{"id": d.doc_id, "text": d.text} for d in qa_set.documents])
    return rag


def _ask(llm, prompt: str) -> Dict[str, Any]:
    try:
        result = llm.chat_completion([{"role": "user", "content": prompt}])
    except LLMError as exc:
        return {"status": "FAIL", "error_type": type(exc).__name__, "error": str(exc)}
    return {"status": "PASS", "answer": result.text, "finish_reason": result.finish_reason,
            "elapsed_seconds": round(result.elapsed_seconds, 3)}


def _summarize(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        kind = "fictional" if row["fictional"] else "general"
        groups[(row["model"], row["mode"], kind)].append(row)
        groups[(row["model"], row["mode"], "all")].append(row)
    summary = []
    for (model, mode, kind), items in sorted(groups.items()):
        correct = sum(r["screening"].startswith("candidate_correct") for r in items)
        incorrect = sum(r["screening"].startswith("candidate_incorrect") for r in items)
        times = sorted(r["elapsed_seconds"] for r in items if r.get("elapsed_seconds"))
        summary.append({"model": model, "mode": mode, "questions": kind, "n": len(items),
                        "correct": correct, "incorrect": incorrect,
                        "manual_review": len(items) - correct - incorrect,
                        "median_seconds": times[len(times) // 2] if times else None})
    return summary


def evaluate_qa(qa_set: QASet, models: Sequence[str],  # pylint: disable=too-many-locals,too-many-arguments
                llm_factory: Callable[[str], Any], embedder, *, embedder_name: str = "",
                top_k: int = 3,
                progress: Callable[[str], None] = lambda m: None) -> Dict[str, Any]:
    """Answer every item closed-book and with RAG for every model."""
    start = time.perf_counter()
    rag = _index(qa_set, embedder, top_k)
    retrieved = {item.item_id: rag.retrieve(item.question, top_k) for item in qa_set.items}
    rag.shutdown()
    index_and_retrieve = time.perf_counter() - start

    rows: List[Dict[str, Any]] = []
    for model in models:
        progress(f"model {model}")
        llm = llm_factory(model)
        try:
            for item in qa_set.items:
                sources = retrieved[item.item_id]
                context = "\n\n".join(f"[{n}] {s['text']}" for n, s in enumerate(sources, 1))
                ranked = [s["document_id"] for s in sources]
                for mode in MODES:
                    prompt = PROMPTS[item.language][mode].format(question=item.question,
                                                                 context=context)
                    answer = _ask(llm, prompt)
                    record = {"test_id": item.item_id, "checker": item.checker,
                              "language": item.language, "expected": item.expected,
                              "answer": answer.get("answer", ""), **answer}
                    screening = assess_answer(record)
                    rows.append({"model": model, "mode": mode, "item_id": item.item_id,
                                 "language": item.language, "fictional": item.fictional,
                                 "question": item.question, "expected": item.expected,
                                 "retrieved": ranked if mode == "rag" else [],
                                 "retrieval_hit": hit_at_k(ranked, item.relevant, top_k)
                                 if mode == "rag" else None,
                                 "screening": screening["status"],
                                 "evidence": screening["evidence"], **answer})
                    progress(f"  {item.item_id} {mode}: {screening['status']}")
        finally:
            llm.shutdown()

    hits = [hit_at_k([s["document_id"] for s in retrieved[i.item_id]], i.relevant, top_k)
            for i in qa_set.items]
    return {"schema": REPORT_SCHEMA, "qa_set": qa_set.name, "qa_set_version": qa_set.version,
            "created_at_utc": datetime.now(timezone.utc).isoformat(), "models": list(models),
            "embedder": embedder_name, "top_k": top_k,
            "retrieval_hit_rate": sum(hits) / len(hits),
            "index_and_retrieve_seconds": round(index_and_retrieve, 2),
            "summary": _summarize(rows), "results": rows}
