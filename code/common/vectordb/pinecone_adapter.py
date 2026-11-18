"""Pinecone vector database adapter implementation.

Talks to an existing index's data plane over REST (stdlib HTTP client, no
SDK). Creating the index is a control-plane operation done once in the
Pinecone console or API; this adapter needs its host.

Configuration:

    host         index host, e.g. "https://<index>-<project>.svc.<region>.pinecone.io"
    api_key / api_key_env    default env PINECONE_API_KEY
    namespace    default "" (the default namespace)
    metric       must match the index: "cosine" (default), "ip" (dotproduct)
                 or "l2" (euclidean)

Pinecone returns similarity for cosine/dotproduct and squared distance for
euclidean; the latter is converted to -distance. Metadata values must be
strings, numbers, booleans or lists of strings (Pinecone restriction).

Previously a stub returning a constant score; the class name and the
VectorDBAdapter methods are unchanged.
"""

# Adapters share the same contract and validation steps by design.
# pylint: disable=duplicate-code,too-many-instance-attributes

import os
from typing import Any, Dict, List, Optional

from ai_platform.common.util.http_json_client import HttpJsonClient, HttpJsonError
from ai_platform.common.vectordb.base import VectorDBAdapter
from ai_platform.common.vectordb.vector_store_support import (
    VectorDBConfigurationError,
    VectorDBError,
    VectorDBNotConnectedError,
    assign_ids,
    check_metric,
    hit,
    validate_batch,
    validate_query,
)

_UPSERT_BATCH = 100


class PineconeAdapter(VectorDBAdapter):
    """Adapter for a Pinecone index."""

    def __init__(self):
        """Initialize Pinecone adapter."""
        self.connected = False
        self.metric = "cosine"
        self.namespace = ""
        self.dimension: Optional[int] = None
        self.last_insert_ids: List[str] = []
        self._client: Optional[HttpJsonClient] = None
        self._count = 0

    def connect(self, config: Dict[str, Any]) -> None:
        """Prepare the data-plane client and read index statistics."""
        host = config.get("host")
        api_key = config.get("api_key") or os.environ.get(
            config.get("api_key_env") or "PINECONE_API_KEY")
        if not host:
            raise VectorDBConfigurationError("pinecone: 'host' of the index is required")
        if not api_key:
            raise VectorDBConfigurationError("pinecone: API key missing (PINECONE_API_KEY)")
        if not host.startswith("http"):
            host = "https://" + host

        self.metric = check_metric(config.get("metric", "cosine"))
        self.namespace = config.get("namespace", "")
        self._client = HttpJsonClient(host, timeout=float(config.get("timeout", 60)),
                                      headers={"Api-Key": api_key})
        stats = self._call("/describe_index_stats", {})
        self.dimension = stats.get("dimension")
        self._count = (stats.get("namespaces", {}).get(self.namespace, {})
                       .get("vectorCount", 0))
        self.connected = True

    def insert(self, vectors: List[List[float]], metadata: List[Dict[str, Any]]) -> None:
        """Upsert vectors in batches of 100."""
        self._require()
        validate_batch(vectors, metadata, self.dimension)
        ids = assign_ids(metadata, self._count)
        records = [{"id": i, "values": list(map(float, v)),
                    "metadata": {k: val for k, val in m.items() if k != "id"}}
                   for i, v, m in zip(ids, vectors, metadata)]
        for start in range(0, len(records), _UPSERT_BATCH):
            self._call("/vectors/upsert", {"vectors": records[start:start + _UPSERT_BATCH],
                                           "namespace": self.namespace})
        self._count += len(ids)
        self.last_insert_ids = ids

    def search(self, query_vector: List[float], top_k: int) -> List[Dict[str, Any]]:
        """Query the index."""
        self._require()
        validate_query(query_vector, self.dimension, top_k)
        answer = self._call("/query", {"vector": list(map(float, query_vector)),
                                       "topK": top_k, "includeMetadata": True,
                                       "namespace": self.namespace})
        results = []
        for match in answer.get("matches", []):
            score = float(match.get("score", 0.0))
            if self.metric == "l2":
                score = -(max(score, 0.0) ** 0.5)
            results.append(hit(match["id"], score, match.get("metadata")))
        return results

    def disconnect(self) -> None:
        """Drop the client."""
        self._client = None
        self.connected = False

    def _call(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return self._client.post(path, payload).data or {}
        except HttpJsonError as exc:
            raise VectorDBError(f"pinecone: {exc}") from exc

    def _require(self) -> None:
        if not self.connected or self._client is None:
            raise VectorDBNotConnectedError(type(self).__name__)
