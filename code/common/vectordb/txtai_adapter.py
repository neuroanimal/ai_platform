"""txtai vector database adapter implementation (https://neuml.github.io/txtai/).

txtai normally embeds text itself. To store vectors computed elsewhere, the
index is built with a ``transform`` function that returns each input
unchanged ("external vectors"), so the vectors passed to ``insert`` are
indexed as given. txtai's index is rebuilt on each ``insert`` with all
vectors seen so far (``Embeddings.index`` replaces, ``upsert`` would need a
content store); fine for the modest sizes txtai's in-memory backends target.

Configuration:

    backend   ANN backend, default "numpy" (exact); "faiss", "hnsw", ...
    metric    only "ip"/"cosine" are meaningful for txtai backends; cosine is
              implemented by L2-normalizing vectors before indexing

Not verified against a live txtai here (the package was not installed when
this was written); unit tests cover the calls through a fake module.
Previously a stub returning a constant score; the class name and the
VectorDBAdapter methods are unchanged.
"""

# Adapters share the same contract and validation steps by design.
# pylint: disable=duplicate-code,too-many-instance-attributes

from typing import Any, Dict, List, Optional

from ai_platform.common.vectordb.base import VectorDBAdapter
from ai_platform.common.vectordb.vector_store_support import (
    VectorDBConfigurationError,
    VectorDBDependencyError,
    VectorDBNotConnectedError,
    assign_ids,
    check_metric,
    hit,
    normalize,
    validate_batch,
    validate_query,
)


def _identity(inputs):
    """txtai transform for external vectors: the input already is the vector."""
    return inputs


class TXTaiAdapter(VectorDBAdapter):
    """Adapter for txtai with externally computed vectors."""

    def __init__(self):
        """Initialize txtai adapter."""
        self.connected = False
        self.metric = "cosine"
        self.backend = "numpy"
        self.last_insert_ids: List[str] = []
        self._embeddings_cls = None
        self._np = None
        self._embeddings = None
        self._ids: List[str] = []
        self._vectors: List[List[float]] = []
        self._metadata: Dict[str, Dict[str, Any]] = {}

    def connect(self, config: Dict[str, Any]) -> None:
        """Import txtai and reset the in-memory index."""
        try:
            from txtai import Embeddings  # pylint: disable=import-outside-toplevel
            import numpy  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise VectorDBDependencyError("TXTaiAdapter", "txtai") from exc
        self.metric = check_metric(config.get("metric", "cosine"))
        if self.metric == "l2":
            raise VectorDBConfigurationError("txtai: metric 'l2' is not supported, use cosine/ip")
        self.backend = config.get("backend", "numpy")
        self._embeddings_cls, self._np = Embeddings, numpy
        self._embeddings, self._ids, self._vectors, self._metadata = None, [], [], {}
        self.connected = True

    def insert(self, vectors: List[List[float]], metadata: List[Dict[str, Any]]) -> None:
        """Add vectors and rebuild the index."""
        self._require()
        validate_batch(vectors, metadata, self._dimension())
        ids = assign_ids(metadata, len(self._ids))
        for record_id, vector, meta in zip(ids, vectors, metadata):
            prepared = normalize(vector) if self.metric == "cosine" else list(vector)
            if record_id in self._metadata:
                self._vectors[self._ids.index(record_id)] = prepared
            else:
                self._ids.append(record_id)
                self._vectors.append(prepared)
            self._metadata[record_id] = dict(meta)

        self._embeddings = self._embeddings_cls(
            {"transform": _identity, "backend": self.backend, "content": False})
        matrix = self._np.asarray(self._vectors, dtype="float32")
        self._embeddings.index([(position, matrix[position], None)
                                for position in range(len(self._ids))])
        self.last_insert_ids = ids

    def search(self, query_vector: List[float], top_k: int) -> List[Dict[str, Any]]:
        """Top-k search; txtai returns (position, score) pairs."""
        self._require()
        validate_query(query_vector, self._dimension(), top_k)
        if self._embeddings is None:
            return []
        query = normalize(query_vector) if self.metric == "cosine" else list(query_vector)
        found = self._embeddings.search(self._np.asarray(query, dtype="float32"), top_k)
        results = []
        for position, score in found:
            record_id = self._ids[int(position)]
            results.append(hit(record_id, score, self._metadata[record_id]))
        return results

    def disconnect(self) -> None:
        """Drop the in-memory index."""
        self._embeddings = None
        self.connected = False

    def _dimension(self) -> Optional[int]:
        return len(self._vectors[0]) if self._vectors else None

    def _require(self) -> None:
        if not self.connected:
            raise VectorDBNotConnectedError(type(self).__name__)
