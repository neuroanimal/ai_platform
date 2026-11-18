"""LanceDB vector database adapter implementation (https://lancedb.github.io/lancedb/).

Embedded (file-based) database through the ``lancedb`` package, imported
lazily. Rows are ``{"id": str, "vector": list[float], "metadata": str}``;
metadata is stored as JSON text so that heterogeneous metadata does not
fight the table's Arrow schema.

Configuration:

    path       database directory, default "./lancedb"
    table      default "ai_platform"
    metric     "cosine" (default), "l2" or "ip" ("dot" in LanceDB)

LanceDB returns ``_distance``: cosine 1 - cos, l2 squared distance,
dot 1 - dot; converted to the package-wide higher-is-better score.

Not verified against a live LanceDB here (the package was not installed
when this was written); unit tests cover the calls through a fake module.
Previously a stub returning a constant score; the class name and the
VectorDBAdapter methods are unchanged.
"""

# Adapters share the same contract and validation steps by design.
# pylint: disable=duplicate-code,too-many-instance-attributes

import json
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

_METRIC = {"cosine": "cosine", "l2": "l2", "ip": "dot"}


class LanceDBAdapter(VectorDBAdapter):
    """Adapter for LanceDB."""

    def __init__(self):
        """Initialize LanceDB adapter."""
        self.connected = False
        self.metric = "cosine"
        self.table_name = "ai_platform"
        self.last_insert_ids: List[str] = []
        self._db = None
        self._table = None

    def connect(self, config: Dict[str, Any]) -> None:
        """Open the database and the table if it exists."""
        try:
            import lancedb  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise VectorDBDependencyError("LanceDBAdapter", "lancedb") from exc
        self.metric = check_metric(config.get("metric", "cosine"))
        self.table_name = config.get("table", "ai_platform")
        self._db = lancedb.connect(config.get("path", "./lancedb"))
        self._table = (self._db.open_table(self.table_name)
                       if self.table_name in self._db.table_names() else None)
        self.connected = True

    def insert(self, vectors: List[List[float]], metadata: List[Dict[str, Any]]) -> None:
        """Append rows; the table is created by the first insert."""
        self._require()
        validate_batch(vectors, metadata, self._dimension())
        if not vectors:
            self.last_insert_ids = []
            return
        start = self._table.count_rows() if self._table is not None else 0
        ids = assign_ids(metadata, start)
        rows = [{"id": i, "vector": list(map(float, v)), "metadata": json.dumps(m)}
                for i, v, m in zip(ids, vectors, metadata)]
        if self._table is None:
            self._table = self._db.create_table(self.table_name, data=rows)
        else:
            self._table.add(rows)
        self.last_insert_ids = ids

    def search(self, query_vector: List[float], top_k: int) -> List[Dict[str, Any]]:
        """Vector search with the configured distance."""
        self._require()
        validate_query(query_vector, self._dimension(), top_k)
        if self._table is None:
            return []
        query = self._table.search(list(map(float, query_vector)))
        # Newer LanceDB calls it distance_type(); older releases metric().
        set_metric = getattr(query, "distance_type", None) or query.metric
        rows = set_metric(_METRIC[self.metric]).limit(top_k).to_list()
        return [hit(r["id"], self._score(float(r["_distance"])),
                    json.loads(r.get("metadata") or "{}")) for r in rows]

    def disconnect(self) -> None:
        """Release handles (data stays on disk)."""
        self._table = None
        self._db = None
        self.connected = False

    def _dimension(self) -> Optional[int]:
        if self._table is None:
            return None
        field = self._table.schema.field("vector")
        return getattr(field.type, "list_size", None)

    def _score(self, distance: float) -> float:
        if self.metric == "l2":
            return -(max(distance, 0.0) ** 0.5)
        return 1.0 - distance

    def _require(self) -> None:
        if not self.connected or self._db is None:
            raise VectorDBNotConnectedError(type(self).__name__)
