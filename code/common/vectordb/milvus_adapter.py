"""Milvus vector database adapter implementation (https://milvus.io).

Uses ``pymilvus.MilvusClient`` (imported lazily), which also covers
Milvus Lite: a ``uri`` ending in ``.db`` is a local file, no server needed.

Configuration:

    uri          "http://127.0.0.1:19530" or "./milvus.db" (Milvus Lite)
    token / token_env   auth token for Zilliz Cloud or secured Milvus
    collection   default "ai_platform"
    metric       "cosine" (default), "l2" or "ip"
    dimension    optional; otherwise taken from the first insert

The collection is created with string primary keys and the dynamic field
enabled, so metadata keys are stored as-is. Milvus returns similarity for
COSINE/IP and squared distance for L2 (converted to -distance).

Not verified against a live Milvus here (pymilvus was not installed when
this was written); unit tests cover the calls made through a fake client.
Previously a stub returning a constant score; the class name and the
VectorDBAdapter methods are unchanged.
"""

# Adapters share the same contract and validation steps by design.
# pylint: disable=duplicate-code,too-many-instance-attributes

import os
from typing import Any, Dict, List, Optional

from ai_platform.common.vectordb.base import VectorDBAdapter
from ai_platform.common.vectordb.vector_store_support import (
    VectorDBDependencyError,
    VectorDBNotConnectedError,
    assign_ids,
    check_metric,
    hit,
    validate_batch,
    validate_query,
)

_METRIC = {"cosine": "COSINE", "l2": "L2", "ip": "IP"}


class MilvusAdapter(VectorDBAdapter):
    """Adapter for Milvus / Milvus Lite."""

    def __init__(self):
        """Initialize Milvus adapter."""
        self.connected = False
        self.metric = "cosine"
        self.collection = "ai_platform"
        self.dimension: Optional[int] = None
        self.last_insert_ids: List[str] = []
        self._client = None
        self._count = 0

    def connect(self, config: Dict[str, Any]) -> None:
        """Create the client; create the collection now if dimension is known."""
        self.metric = check_metric(config.get("metric", "cosine"))
        self.collection = config.get("collection", "ai_platform")
        self.dimension = config.get("dimension")
        self._client = config.get("client")
        if self._client is None:
            try:
                from pymilvus import MilvusClient  # pylint: disable=import-outside-toplevel
            except ImportError as exc:
                raise VectorDBDependencyError("MilvusAdapter", "pymilvus") from exc
            token = config.get("token") or os.environ.get(config.get("token_env") or "")
            self._client = MilvusClient(uri=config.get("uri", "./milvus.db"), token=token or "")

        if self._client.has_collection(self.collection):
            stats = self._client.get_collection_stats(self.collection)
            self._count = int(stats.get("row_count", 0))
        elif self.dimension:
            self._create(self.dimension)
        self.connected = True

    def insert(self, vectors: List[List[float]], metadata: List[Dict[str, Any]]) -> None:
        """Upsert rows (id, vector, metadata keys as dynamic fields)."""
        self._require()
        dimension = validate_batch(vectors, metadata, self.dimension)
        if not vectors:
            self.last_insert_ids = []
            return
        if not self._client.has_collection(self.collection):
            self.dimension = dimension
            self._create(dimension)
        ids = assign_ids(metadata, self._count)
        rows = [{**{k: v for k, v in m.items() if k != "id"}, "id": i,
                 "vector": list(map(float, vec))}
                for i, vec, m in zip(ids, vectors, metadata)]
        self._client.upsert(collection_name=self.collection, data=rows)
        self._count += len(ids)
        self.last_insert_ids = ids

    def search(self, query_vector: List[float], top_k: int) -> List[Dict[str, Any]]:
        """ANN search returning all dynamic fields as metadata."""
        self._require()
        validate_query(query_vector, self.dimension, top_k)
        if not self._client.has_collection(self.collection):
            return []
        answer = self._client.search(collection_name=self.collection,
                                     data=[list(map(float, query_vector))],
                                     limit=top_k, output_fields=["*"])
        results = []
        for item in answer[0]:
            entity = dict(item.get("entity") or {})
            entity.pop("vector", None)
            entity.pop("id", None)
            value = float(item["distance"])
            score = -(max(value, 0.0) ** 0.5) if self.metric == "l2" else value
            results.append(hit(item["id"], score, entity))
        return results

    def disconnect(self) -> None:
        """Close the client."""
        if self._client is not None and hasattr(self._client, "close"):
            self._client.close()
        self._client = None
        self.connected = False

    def _create(self, dimension: int) -> None:
        self._client.create_collection(
            collection_name=self.collection, dimension=dimension,
            metric_type=_METRIC[self.metric], id_type="string", max_length=512,
            enable_dynamic_field=True,
        )

    def _require(self) -> None:
        if not self.connected or self._client is None:
            raise VectorDBNotConnectedError(type(self).__name__)
