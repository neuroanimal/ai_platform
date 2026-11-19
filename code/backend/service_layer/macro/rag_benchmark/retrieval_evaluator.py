"""
Compare embedders on a retrieval set.

For each embedder, the set's documents are indexed with the platform's own
RAG pipeline (``NativeRAGAdapter`` over an in-memory SQLite vector store,
one chunk per document) and every query is retrieved; the ranking is
scored with ``common.evaluation.retrieval_metrics``. The report holds the
ranking of every query, so a surprising number can be traced to its query.

Embedders come from a factory ``name -> Embedder`` chosen by the caller
(the CLI maps names such as ``hashing`` or ``ollama:bge-m3``).
"""

import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Sequence

from ai_platform.backend.domain_layer.business_logic.rag_benchmark.retrieval_sets import (
    RetrievalSet,
    get_retrieval_set,
    list_retrieval_sets,
)
from ai_platform.common.evaluation.retrieval_metrics import aggregate_retrieval, score_query
from ai_platform.common.rag.embedder import EmbeddingError
from ai_platform.common.rag.native_rag_adapter import NativeRAGAdapter

REPORT_SCHEMA = "ai_platform.retrieval_benchmark.report/1"

__all__ = ["evaluate_embedders", "get_retrieval_set", "list_retrieval_sets", "REPORT_SCHEMA"]


def _evaluate_one(name: str, embedder, retrieval_set: RetrievalSet, top_k: int) -> Dict[str, Any]:
    documents = retrieval_set.by_id
    rag = NativeRAGAdapter()
    # One chunk per document: the set's documents are short on purpose.
    rag.initialize({"embedder": embedder, "top_k": top_k, "chunk_size": 4000,
                    "chunk_overlap": 0})
    start = time.perf_counter()
    rag.ingest([{"id": d.doc_id, "text": d.text, "metadata": {"language": d.language}}
                for d in retrieval_set.documents])
    index_seconds = time.perf_counter() - start

    rows, by_direction = [], defaultdict(list)
    start = time.perf_counter()
    for query in retrieval_set.queries:
        ranked = [s["document_id"] for s in rag.retrieve(query.text, top_k)]
        scores = score_query(ranked, query.relevant)
        direction = query.direction(documents)
        by_direction[direction].append(scores)
        rows.append({"embedder": name, "query_id": query.query_id, "query": query.text,
                     "direction": direction, "relevant": list(query.relevant),
                     "ranked": ranked, **scores})
    query_seconds = time.perf_counter() - start
    rag.shutdown()
    return {
        "embedder": name, "status": "PASS",
        "index_seconds": round(index_seconds, 3),
        "query_seconds_mean": round(query_seconds / len(retrieval_set.queries), 4),
        "metrics": aggregate_retrieval([{k: r[k] for k in r if k.startswith(("hit", "recall"))
                                         or k == "rr"} for r in rows]),
        "by_direction": {d: aggregate_retrieval(v) for d, v in sorted(by_direction.items())},
        "queries": rows,
    }


def evaluate_embedders(retrieval_set: RetrievalSet, embedder_names: Sequence[str],
                       factory: Callable[[str], Any], top_k: int = 5) -> Dict[str, Any]:
    """Evaluate each named embedder; an unavailable one is recorded as FAIL."""
    results: List[Dict[str, Any]] = []
    for name in embedder_names:
        try:
            results.append(_evaluate_one(name, factory(name), retrieval_set, top_k))
        except (EmbeddingError, ValueError) as exc:
            results.append({"embedder": name, "status": "FAIL",
                            "error_type": type(exc).__name__, "error": str(exc)})
    return {"schema": REPORT_SCHEMA, "retrieval_set": retrieval_set.name,
            "retrieval_set_version": retrieval_set.version,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "top_k": top_k, "documents": len(retrieval_set.documents),
            "queries": len(retrieval_set.queries), "results": results}
