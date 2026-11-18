"""OpenSearch vector database adapter implementation.

Uses the REST API (k-NN plugin: ``knn_vector`` field, HNSW on the Lucene
engine, ``knn`` query) through the stdlib HTTP client - no SDK required.
Configuration and score conversion: see ``search_engine_support.py``.

Previously a stub returning a constant score; the class name and the
VectorDBAdapter methods are unchanged.
"""

from typing import Any, Dict, List

from ai_platform.common.vectordb.search_engine_support import SearchEngineVectorAdapter

_SPACE = {"cosine": "cosinesimil", "l2": "l2", "ip": "innerproduct"}


class OpenSearchAdapter(SearchEngineVectorAdapter):
    """Adapter for OpenSearch."""

    ENGINE = "opensearch"

    def _mapping(self, dimension: int) -> Dict[str, Any]:
        return {
            "settings": {"index": {"knn": True}},
            "mappings": {"properties": {
                "record_id": {"type": "keyword"},
                "metadata_json": {"type": "text", "index": False},
                "vector": {"type": "knn_vector", "dimension": dimension,
                           "method": {"name": "hnsw", "engine": "lucene",
                                      "space_type": _SPACE[self.metric]}},
            }},
        }

    def _knn_query(self, vector: List[float], top_k: int) -> Dict[str, Any]:
        return {
            "size": top_k,
            "query": {"knn": {"vector": {"vector": vector, "k": top_k}}},
            "_source": ["record_id", "metadata_json"],
        }
