"""Weaviate vector database adapter implementation.

REST + GraphQL API (Weaviate 1.x) through the stdlib HTTP client - no SDK.
The collection ("class") is created with ``vectorizer: none`` so the vectors
passed to ``insert`` are stored as given.

Configuration:

    url          default "http://127.0.0.1:8080"
    collection   class name, default "AiPlatform" (Weaviate capitalizes it)
    metric       "cosine" (default), "l2" (l2-squared) or "ip" (dot)
    api_key / api_key_env    Bearer token for Weaviate Cloud or API-key auth

Weaviate reports distances: cosine 1 - cos, l2-squared d^2, dot -dot; they
are converted to the package-wide higher-is-better score. Record ids are
mapped to deterministic UUIDv5 object ids; the original id and the
metadata (as JSON text) are stored as properties.

Previously a stub returning a constant score; the class name and the
VectorDBAdapter methods are unchanged.
"""

# Adapters share the same contract and validation steps by design.
# pylint: disable=duplicate-code,too-many-instance-attributes

import json
import os
import uuid
from typing import Any, Dict, List, Optional

from ai_platform.common.util.http_json_client import HttpJsonClient, HttpJsonError, HttpStatusError
from ai_platform.common.vectordb.base import VectorDBAdapter
from ai_platform.common.vectordb.vector_store_support import (
    VectorDBError,
    VectorDBNotConnectedError,
    assign_ids,
    check_metric,
    hit,
    validate_batch,
    validate_query,
)

_DISTANCE = {"cosine": "cosine", "l2": "l2-squared", "ip": "dot"}
_ID_NAMESPACE = uuid.UUID("0b8a8d4e-3f2c-4f39-9d0a-5e7c2b1a9f10")


class WeaviateAdapter(VectorDBAdapter):
    """Adapter for Weaviate."""

    def __init__(self):
        """Initialize Weaviate adapter."""
        self.connected = False
        self.metric = "cosine"
        self.collection = "AiPlatform"
        self.last_insert_ids: List[str] = []
        self._client: Optional[HttpJsonClient] = None
        self._count = 0

    def connect(self, config: Dict[str, Any]) -> None:
        """Create the client and the collection if it does not exist."""
        self.metric = check_metric(config.get("metric", "cosine"))
        name = config.get("collection", "AiPlatform")
        self.collection = name[:1].upper() + name[1:]
        api_key = config.get("api_key") or os.environ.get(config.get("api_key_env") or "")
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = HttpJsonClient(config.get("url", "http://127.0.0.1:8080"),
                                      timeout=float(config.get("timeout", 60)), headers=headers)
        try:
            self._client.get(f"/v1/schema/{self.collection}")
        except HttpStatusError as exc:
            if exc.status != 404:
                raise VectorDBError(f"weaviate: {exc}") from exc
            self._call("POST", "/v1/schema", {
                "class": self.collection,
                "vectorizer": "none",
                "vectorIndexConfig": {"distance": _DISTANCE[self.metric]},
                "properties": [{"name": "record_id", "dataType": ["text"]},
                               {"name": "metadata_json", "dataType": ["text"]}],
            })
        except HttpJsonError as exc:
            raise VectorDBError(f"weaviate: {exc}") from exc
        self.connected = True

    def insert(self, vectors: List[List[float]], metadata: List[Dict[str, Any]]) -> None:
        """Batch-insert objects with explicit vectors."""
        self._require()
        validate_batch(vectors, metadata, None)
        ids = assign_ids(metadata, self._count)
        answer = self._call("POST", "/v1/batch/objects", {"objects": [
            {"class": self.collection,
             "id": str(uuid.uuid5(_ID_NAMESPACE, record_id)),
             "vector": list(map(float, vector)),
             "properties": {"record_id": record_id, "metadata_json": json.dumps(meta)}}
            for record_id, vector, meta in zip(ids, vectors, metadata)
        ]})
        errors = [o["result"]["errors"] for o in (answer or [])
                  if isinstance(o, dict) and (o.get("result") or {}).get("errors")]
        if errors:
            raise VectorDBError(f"weaviate: batch insert failed: {errors[:3]}")
        self._count += len(ids)
        self.last_insert_ids = ids

    def search(self, query_vector: List[float], top_k: int) -> List[Dict[str, Any]]:
        """nearVector GraphQL query."""
        self._require()
        validate_query(query_vector, None, top_k)
        vector = ",".join(repr(float(x)) for x in query_vector)
        query = (f"{{ Get {{ {self.collection}(nearVector: {{vector: [{vector}]}}, "
                 f"limit: {int(top_k)}) "
                 "{ record_id metadata_json _additional { distance } } } }")
        answer = self._call("POST", "/v1/graphql", {"query": query})
        if answer.get("errors"):
            raise VectorDBError(f"weaviate: {answer['errors']}")
        results = []
        for item in (answer.get("data") or {}).get("Get", {}).get(self.collection) or []:
            distance = float(item["_additional"]["distance"])
            results.append(hit(item["record_id"], self._score(distance),
                               json.loads(item.get("metadata_json") or "{}")))
        return results

    def disconnect(self) -> None:
        """Drop the client."""
        self._client = None
        self.connected = False

    def _score(self, distance: float) -> float:
        if self.metric == "cosine":
            return 1.0 - distance
        if self.metric == "ip":
            return -distance
        return -(max(distance, 0.0) ** 0.5)

    def _call(self, method: str, path: str, payload: Any):
        try:
            return self._client.request(method, path, payload).data
        except HttpJsonError as exc:
            raise VectorDBError(f"weaviate: {exc}") from exc

    def _require(self) -> None:
        if not self.connected or self._client is None:
            raise VectorDBNotConnectedError(type(self).__name__)
