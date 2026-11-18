"""Qdrant vector database adapter implementation (https://qdrant.tech).

Configuration (one client mode):

    url [api_key | api_key_env]   remote server, e.g. "http://127.0.0.1:6333"
    path                          local on-disk mode (no server)
    (neither)                     in-memory local mode (":memory:")

    collection   default "ai_platform"
    metric       "cosine" (default), "l2" (Euclid) or "ip" (Dot)
    dimension    optional; otherwise taken from the first insert

Qdrant point ids must be unsigned integers or UUIDs. Numeric ids are sent
as integers; any other ``metadata["id"]`` is mapped to a deterministic
UUIDv5 and the original id is kept in the payload under ``_id``.
Qdrant returns Euclid as a distance (lower is better); it is negated so
that ``score`` is higher-is-better for every metric.

Previously a stub returning a constant score; the class name and the
VectorDBAdapter methods are unchanged.
"""

# Adapters share the same contract and validation steps by design.
# pylint: disable=duplicate-code,too-many-instance-attributes

import os
import uuid
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

# Fixed namespace so that the same textual id always maps to the same UUID.
_ID_NAMESPACE = uuid.UUID("6f1b3c1e-5a52-4c8e-9f0e-a1b2c3d4e5f6")


def to_point_id(record_id: str):
    """Map an arbitrary id to a valid Qdrant point id."""
    if record_id.isdigit():
        return int(record_id)
    try:
        return str(uuid.UUID(record_id))
    except ValueError:
        return str(uuid.uuid5(_ID_NAMESPACE, record_id))


class QdrantAdapter(VectorDBAdapter):
    """Adapter for Qdrant."""

    def __init__(self):
        """Initialize Qdrant adapter."""
        self.connected = False
        self.metric = "cosine"
        self.collection = "ai_platform"
        self.dimension: Optional[int] = None
        self.last_insert_ids: List[str] = []
        self._client = None
        self._models = None
        self._count = 0

    def connect(self, config: Dict[str, Any]) -> None:
        """Create the client; the collection is created on first insert if missing."""
        try:
            from qdrant_client import QdrantClient, models  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise VectorDBDependencyError("QdrantAdapter", "qdrant-client") from exc

        self._models = models
        self.metric = check_metric(config.get("metric", "cosine"))
        self.collection = config.get("collection", "ai_platform")
        self.dimension = config.get("dimension")

        if config.get("url"):
            api_key = config.get("api_key") or os.environ.get(config.get("api_key_env") or "")
            self._client = QdrantClient(url=config["url"], api_key=api_key or None)
        elif config.get("path"):
            self._client = QdrantClient(path=config["path"])
        else:
            self._client = QdrantClient(location=":memory:")

        if self._client.collection_exists(self.collection):
            info = self._client.get_collection(self.collection)
            self.dimension = info.config.params.vectors.size
            self._count = self._client.count(self.collection).count
        elif self.dimension:
            self._create(self.dimension)
        self.connected = True

    def insert(self, vectors: List[List[float]], metadata: List[Dict[str, Any]]) -> None:
        """Upsert points into the collection."""
        self._require()
        dimension = validate_batch(vectors, metadata, self.dimension)
        if not vectors:
            self.last_insert_ids = []
            return
        if not self._client.collection_exists(self.collection):
            self.dimension = dimension
            self._create(dimension)

        ids = assign_ids(metadata, self._count)
        points = [
            self._models.PointStruct(id=to_point_id(i), vector=list(map(float, v)),
                                     payload={**m, "_id": i})
            for i, v, m in zip(ids, vectors, metadata)
        ]
        self._client.upsert(collection_name=self.collection, points=points, wait=True)
        self._count += len(ids)
        self.last_insert_ids = ids

    def search(self, query_vector: List[float], top_k: int) -> List[Dict[str, Any]]:
        """Nearest-neighbour query."""
        self._require()
        validate_query(query_vector, self.dimension, top_k)
        if not self._client.collection_exists(self.collection):
            return []
        answer = self._client.query_points(
            collection_name=self.collection,
            query=list(map(float, query_vector)),
            limit=top_k,
            with_payload=True,
        )
        results = []
        for point in answer.points:
            payload = dict(point.payload or {})
            record_id = payload.pop("_id", point.id)
            score = -point.score if self.metric == "l2" else point.score
            results.append(hit(record_id, score, payload))
        return results

    def disconnect(self) -> None:
        """Close the client."""
        if self._client is not None:
            self._client.close()
        self._client = None
        self.connected = False

    def _create(self, dimension: int) -> None:
        distance = {"cosine": self._models.Distance.COSINE,
                    "l2": self._models.Distance.EUCLID,
                    "ip": self._models.Distance.DOT}[self.metric]
        self._client.create_collection(
            collection_name=self.collection,
            vectors_config=self._models.VectorParams(size=dimension, distance=distance),
        )

    def _require(self) -> None:
        if not self.connected or self._client is None:
            raise VectorDBNotConnectedError(type(self).__name__)
