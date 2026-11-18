"""Elasticsearch vector database adapter implementation.

Uses the REST API (``dense_vector`` field + top-level ``knn`` search,
Elasticsearch 8.x) through the stdlib HTTP client - no SDK required.
Configuration and score conversion: see ``search_engine_support.py``.
``metric="ip"`` maps to ``max_inner_product`` (Elasticsearch 8.11+).

Previously a stub returning a constant score; the class name and the
VectorDBAdapter methods are unchanged.
"""

from typing import Any, Dict, List

from ai_platform.common.vectordb.search_engine_support import SearchEngineVectorAdapter

_SIMILARITY = {"cosine": "cosine", "l2": "l2_norm", "ip": "max_inner_product"}


class ElasticsearchAdapter(SearchEngineVectorAdapter):
    """Adapter for Elasticsearch."""

    ENGINE = "elasticsearch"

    def _mapping(self, dimension: int) -> Dict[str, Any]:
        return {"mappings": {"properties": {
            "record_id": {"type": "keyword"},
            "metadata_json": {"type": "text", "index": False},
            "vector": {"type": "dense_vector", "dims": dimension, "index": True,
                       "similarity": _SIMILARITY[self.metric]},
        }}}

    def _knn_query(self, vector: List[float], top_k: int) -> Dict[str, Any]:
        return {
            "knn": {"field": "vector", "query_vector": vector, "k": top_k,
                    "num_candidates": max(100, top_k)},
            "size": top_k,
            "_source": ["record_id", "metadata_json"],
        }
