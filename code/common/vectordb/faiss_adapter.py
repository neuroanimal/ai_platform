"""FAISS vector database adapter implementation.

In-process index (https://github.com/facebookresearch/faiss). Metadata and
ids are kept alongside the index in Python, because a flat FAISS index only
stores vectors.

Configuration:

    metric     "cosine" (default), "l2" or "ip"
    dimension  optional; otherwise taken from the first insert
    path       optional file: loaded on connect if it exists, written on
               disconnect (index + "<path>.meta.json" with ids and metadata)

Cosine is implemented as inner product on L2-normalized vectors.
Previously a stub returning a constant score; the class name and the
VectorDBAdapter methods are unchanged.
"""

# Adapters share the same contract and validation steps by design.
# pylint: disable=duplicate-code,too-many-instance-attributes

import json
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


class FAISSAdapter(VectorDBAdapter):
    """Adapter for FAISS vector database."""

    def __init__(self):
        """Initialize FAISS adapter."""
        self.connected = False
        self.metric = "cosine"
        self.dimension: Optional[int] = None
        self.path: Optional[str] = None
        self.last_insert_ids: List[str] = []
        self._faiss = None
        self._np = None
        self._index = None
        self._ids: List[str] = []
        self._metadata: List[Dict[str, Any]] = []

    def connect(self, config: Dict[str, Any]) -> None:
        """Connect to FAISS."""
        try:
            import faiss  # pylint: disable=import-outside-toplevel
            import numpy  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise VectorDBDependencyError("FAISSAdapter", "faiss-cpu") from exc

        self._faiss, self._np = faiss, numpy
        self.metric = check_metric(config.get("metric", "cosine"))
        self.dimension = config.get("dimension")
        self.path = config.get("path")
        self._index, self._ids, self._metadata = None, [], []

        if self.path and os.path.exists(self.path):
            self._index = faiss.read_index(self.path)
            self.dimension = self._index.d
            with open(self.path + ".meta.json", encoding="utf-8") as handle:
                stored = json.load(handle)
            self._ids, self._metadata = stored["ids"], stored["metadata"]
            self.metric = stored.get("metric", self.metric)
        elif self.dimension:
            self._index = self._new_index(self.dimension)

        self.connected = True

    def insert(self, vectors: List[List[float]], metadata: List[Dict[str, Any]]) -> None:
        """Insert vectors into FAISS."""
        self._require()
        dimension = validate_batch(vectors, metadata, self.dimension)
        if not vectors:
            self.last_insert_ids = []
            return
        if self._index is None:
            self.dimension = dimension
            self._index = self._new_index(dimension)

        matrix = self._prepare(vectors)
        self._index.add(matrix)
        ids = assign_ids(metadata, len(self._ids))
        self._ids.extend(ids)
        self._metadata.extend(dict(m) for m in metadata)
        self.last_insert_ids = ids

    def search(self, query_vector: List[float], top_k: int) -> List[Dict[str, Any]]:
        """Search for similar vectors in FAISS."""
        self._require()
        validate_query(query_vector, self.dimension, top_k)
        if self._index is None or self._index.ntotal == 0:
            return []

        k = min(top_k, self._index.ntotal)
        values, positions = self._index.search(self._prepare([query_vector]), k)
        results = []
        for value, position in zip(values[0], positions[0]):
            if position < 0:
                continue
            # IndexFlatL2 returns squared distances; score = -distance.
            score = -float(value) ** 0.5 if self.metric == "l2" else float(value)
            results.append(hit(self._ids[position], score, self._metadata[position]))
        return results

    def disconnect(self) -> None:
        """Disconnect from FAISS."""
        if self.connected and self.path and self._index is not None:
            self._faiss.write_index(self._index, self.path)
            with open(self.path + ".meta.json", "w", encoding="utf-8") as handle:
                json.dump({"ids": self._ids, "metadata": self._metadata,
                           "metric": self.metric}, handle)
        self.connected = False

    def _new_index(self, dimension: int):
        if self.metric == "l2":
            return self._faiss.IndexFlatL2(dimension)
        return self._faiss.IndexFlatIP(dimension)

    def _prepare(self, vectors: List[List[float]]):
        matrix = self._np.asarray(vectors, dtype="float32")
        if self.metric == "cosine":
            self._faiss.normalize_L2(matrix)
        return matrix

    def _require(self) -> None:
        if not self.connected:
            raise VectorDBNotConnectedError(type(self).__name__)
