"""ChromaDB vector database adapter implementation (https://docs.trychroma.com).

Configuration (one of the three client modes):

    path        persistent local database directory  -> PersistentClient
    host, port  remote Chroma server                  -> HttpClient
    (neither)   in-memory database                    -> EphemeralClient
                (shared by all adapters in one process: use distinct
                collection names to keep them apart)

    collection  collection name, default "ai_platform"
    metric      "cosine" (default), "l2" or "ip"; fixed when the collection
                is created (``hnsw:space``)

Chroma reports distances (cosine: 1 - cos, l2: squared distance,
ip: 1 - dot); they are converted to the package-wide higher-is-better score.
Previously a stub returning a constant score; the class name and the
VectorDBAdapter methods are unchanged.
"""

# Adapters share the same contract and validation steps by design.
# pylint: disable=duplicate-code,too-many-instance-attributes

from typing import Any, Dict, List

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


class ChromaDBAdapter(VectorDBAdapter):
    """Adapter for ChromaDB."""

    def __init__(self):
        """Initialize ChromaDB adapter."""
        self.connected = False
        self.metric = "cosine"
        self.last_insert_ids: List[str] = []
        self._client = None
        self._collection = None

    def connect(self, config: Dict[str, Any]) -> None:
        """Create the client and get or create the collection."""
        try:
            import chromadb  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise VectorDBDependencyError("ChromaDBAdapter", "chromadb") from exc

        self.metric = check_metric(config.get("metric", "cosine"))
        if config.get("path"):
            self._client = chromadb.PersistentClient(path=config["path"])
        elif config.get("host"):
            self._client = chromadb.HttpClient(host=config["host"], port=config.get("port", 8000))
        else:
            self._client = chromadb.EphemeralClient()

        self._collection = self._client.get_or_create_collection(
            name=config.get("collection", "ai_platform"),
            metadata={"hnsw:space": self.metric},
        )
        self.connected = True

    def insert(self, vectors: List[List[float]], metadata: List[Dict[str, Any]]) -> None:
        """Insert vectors into ChromaDB (upsert by id)."""
        self._require()
        validate_batch(vectors, metadata, None)
        if not vectors:
            self.last_insert_ids = []
            return
        ids = assign_ids(metadata, self._collection.count())
        # Chroma rejects empty metadata dicts; None means "no metadata".
        self._collection.upsert(
            ids=ids,
            embeddings=[list(map(float, v)) for v in vectors],
            metadatas=[dict(m) if m else None for m in metadata],
        )
        self.last_insert_ids = ids

    def search(self, query_vector: List[float], top_k: int) -> List[Dict[str, Any]]:
        """Search for similar vectors in ChromaDB."""
        self._require()
        validate_query(query_vector, None, top_k)
        count = self._collection.count()
        if count == 0:
            return []
        answer = self._collection.query(
            query_embeddings=[list(map(float, query_vector))],
            n_results=min(top_k, count),
            include=["distances", "metadatas"],
        )
        results = []
        for record_id, distance, meta in zip(answer["ids"][0], answer["distances"][0],
                                             answer["metadatas"][0]):
            results.append(hit(record_id, self._score(distance), meta))
        return results

    def disconnect(self) -> None:
        """Release the client (persistent data stays on disk)."""
        self._collection = None
        self._client = None
        self.connected = False

    def _score(self, distance: float) -> float:
        if self.metric == "cosine":
            return 1.0 - distance
        if self.metric == "ip":
            return 1.0 - distance
        return -(max(distance, 0.0) ** 0.5)

    def _require(self) -> None:
        if not self.connected or self._collection is None:
            raise VectorDBNotConnectedError(type(self).__name__)
