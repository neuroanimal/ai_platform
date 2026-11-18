"""SQLite vector store adapter implementation.

Standard-library only: vectors are stored as JSON arrays in a table and
searched by exact brute force in Python. Suitable for small collections,
tests and offline tooling; for large collections use FAISS, Qdrant or
pgvector.

Configuration:

    path    database file, default ":memory:"
    table   table name, default "vectors" (letters, digits, underscore)
    metric  "cosine" (default), "l2" or "ip"

Previously a stub returning a constant score; the class name and the
VectorDBAdapter methods are unchanged.
"""

# Adapters share the same contract and validation steps by design.
# pylint: disable=duplicate-code,too-many-instance-attributes

import heapq
import json
import re
import sqlite3
from typing import Any, Dict, List, Optional

from ai_platform.common.vectordb.base import VectorDBAdapter
from ai_platform.common.vectordb.vector_store_support import (
    VectorDBConfigurationError,
    VectorDBNotConnectedError,
    assign_ids,
    check_metric,
    hit,
    similarity,
    validate_batch,
    validate_query,
)

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class SQLiteAdapter(VectorDBAdapter):
    """Adapter for a SQLite-backed exact vector store."""

    def __init__(self):
        """Initialize SQLite adapter."""
        self.connected = False
        self.metric = "cosine"
        self.table = "vectors"
        self.last_insert_ids: List[str] = []
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self, config: Dict[str, Any]) -> None:
        """Open (and create if needed) the database and table."""
        self.metric = check_metric(config.get("metric", "cosine"))
        self.table = config.get("table", "vectors")
        # The table name is interpolated into SQL, so it must be an identifier.
        if not _IDENTIFIER.match(self.table):
            raise VectorDBConfigurationError(f"invalid table name: {self.table!r}")

        self._conn = sqlite3.connect(config.get("path", ":memory:"))
        self._conn.execute(
            f"CREATE TABLE IF NOT EXISTS {self.table} ("
            "seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL, "
            "dimension INTEGER NOT NULL, vector TEXT NOT NULL, metadata TEXT NOT NULL)"
        )
        self._conn.commit()
        self.connected = True

    def insert(self, vectors: List[List[float]], metadata: List[Dict[str, Any]]) -> None:
        """Insert (or replace by id) vectors with metadata."""
        conn = self._require()
        validate_batch(vectors, metadata, self._dimension())
        next_id = conn.execute(f"SELECT COALESCE(MAX(seq), 0) FROM {self.table}").fetchone()[0]
        ids = assign_ids(metadata, next_id)
        conn.executemany(
            f"INSERT OR REPLACE INTO {self.table} (id, dimension, vector, metadata) "
            "VALUES (?, ?, ?, ?)",
            [(i, len(v), json.dumps(list(v)), json.dumps(m))
             for i, v, m in zip(ids, vectors, metadata)],
        )
        conn.commit()
        self.last_insert_ids = ids

    def search(self, query_vector: List[float], top_k: int) -> List[Dict[str, Any]]:
        """Exact top-k search over every stored vector."""
        conn = self._require()
        validate_query(query_vector, self._dimension(), top_k)
        rows = conn.execute(f"SELECT id, vector, metadata FROM {self.table}")
        scored = (
            (similarity(query_vector, json.loads(vector), self.metric), record_id, meta)
            for record_id, vector, meta in rows
        )
        best = heapq.nlargest(top_k, scored, key=lambda item: item[0])
        return [hit(record_id, score, json.loads(meta)) for score, record_id, meta in best]

    def disconnect(self) -> None:
        """Close the database."""
        if self._conn is not None:
            self._conn.close()
        self._conn = None
        self.connected = False

    def _dimension(self) -> Optional[int]:
        row = self._conn.execute(f"SELECT dimension FROM {self.table} LIMIT 1").fetchone()
        return row[0] if row else None

    def _require(self) -> sqlite3.Connection:
        if not self.connected or self._conn is None:
            raise VectorDBNotConnectedError(type(self).__name__)
        return self._conn
