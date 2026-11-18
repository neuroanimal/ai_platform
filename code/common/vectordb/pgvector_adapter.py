"""PostgreSQL pgvector adapter implementation (https://github.com/pgvector/pgvector).

Uses psycopg 3 (imported lazily). Table layout::

    <table>(id TEXT PRIMARY KEY, embedding vector(<dimension>), metadata JSONB)

Configuration:

    dsn          libpq connection string, e.g. "postgresql://user@host/db";
                 or ``connection``: an already open psycopg connection
    table        default "ai_platform_vectors" (letters, digits, underscore)
    metric       "cosine" (default) -> <=>, "l2" -> <->, "ip" -> <#>
    dimension    optional; otherwise taken from the first insert
    create_extension   run CREATE EXTENSION IF NOT EXISTS vector (default True)

All values are passed as query parameters; only the validated table name
is interpolated. ``<#>`` returns the negative inner product, so every
metric converts with ``score = -distance`` except cosine (1 - distance).

Previously a stub returning a constant score; the class name and the
VectorDBAdapter methods are unchanged.
"""

# Adapters share the same contract and validation steps by design.
# pylint: disable=duplicate-code,too-many-instance-attributes

import json
import re
from typing import Any, Dict, List, Optional

from ai_platform.common.vectordb.base import VectorDBAdapter
from ai_platform.common.vectordb.vector_store_support import (
    VectorDBConfigurationError,
    VectorDBDependencyError,
    VectorDBNotConnectedError,
    assign_ids,
    check_metric,
    hit,
    validate_batch,
    validate_query,
)

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")


def vector_literal(vector: List[float]) -> str:
    """pgvector text representation, passed as a parameter and cast in SQL."""
    return "[" + ",".join(repr(float(x)) for x in vector) + "]"


class PGVectorAdapter(VectorDBAdapter):
    """Adapter for PostgreSQL with the pgvector extension."""

    EXTENSION = "vector"
    OPERATORS = {"cosine": "<=>", "l2": "<->", "ip": "<#>"}

    def __init__(self):
        """Initialize pgvector adapter."""
        self.connected = False
        self.metric = "cosine"
        self.table = "ai_platform_vectors"
        self.dimension: Optional[int] = None
        self.last_insert_ids: List[str] = []
        self._conn = None
        self._owns_connection = False

    # -- SQL fragments subclasses may override ---------------------------

    def _column_type(self, dimension: int) -> str:
        return f"vector({int(dimension)})"

    def _distance_sql(self) -> str:
        return f"embedding {self.OPERATORS[self.metric]} %s::vector"

    def _value_sql(self) -> str:
        return "%s::vector"

    def _to_param(self, vector: List[float]) -> Any:
        return vector_literal(vector)

    # -- VectorDBAdapter ---------------------------------------------------

    def connect(self, config: Dict[str, Any]) -> None:
        """Open the connection and create extension/table when needed."""
        self.metric = check_metric(config.get("metric", "cosine"))
        self.table = config.get("table", "ai_platform_vectors")
        if not _IDENTIFIER.match(self.table):
            raise VectorDBConfigurationError(f"invalid table name: {self.table!r}")
        self.dimension = config.get("dimension")

        self._conn = config.get("connection")
        self._owns_connection = self._conn is None
        if self._conn is None:
            try:
                import psycopg  # pylint: disable=import-outside-toplevel
            except ImportError as exc:
                raise VectorDBDependencyError(type(self).__name__, "psycopg") from exc
            if not config.get("dsn"):
                raise VectorDBConfigurationError("'dsn' or 'connection' is required")
            self._conn = psycopg.connect(config["dsn"])

        if config.get("create_extension", True):
            self._execute(f"CREATE EXTENSION IF NOT EXISTS {self.EXTENSION}")
        if self.dimension:
            self._create_table(self.dimension)
        self.connected = True

    def insert(self, vectors: List[List[float]], metadata: List[Dict[str, Any]]) -> None:
        """Insert or update rows by id."""
        self._require()
        dimension = validate_batch(vectors, metadata, self.dimension)
        if not vectors:
            self.last_insert_ids = []
            return
        if not self.dimension:
            self.dimension = dimension
            self._create_table(dimension)

        start = self._execute(f"SELECT COUNT(*) FROM {self.table}", fetch=True)[0][0]
        ids = assign_ids(metadata, start)
        sql = (f"INSERT INTO {self.table} (id, embedding, metadata) "
               f"VALUES (%s, {self._value_sql()}, %s::jsonb) "
               "ON CONFLICT (id) DO UPDATE SET embedding = EXCLUDED.embedding, "
               "metadata = EXCLUDED.metadata")
        with self._conn.cursor() as cur:
            cur.executemany(sql, [(i, self._to_param(v), json.dumps(m))
                                  for i, v, m in zip(ids, vectors, metadata)])
        self._conn.commit()
        self.last_insert_ids = ids

    def search(self, query_vector: List[float], top_k: int) -> List[Dict[str, Any]]:
        """ORDER BY distance LIMIT top_k."""
        self._require()
        validate_query(query_vector, self.dimension, top_k)
        if not self.dimension:
            return []
        distance = self._distance_sql()
        rows = self._execute(
            f"SELECT id, metadata, {distance} AS distance FROM {self.table} "
            f"ORDER BY distance LIMIT %s",
            (self._to_param(query_vector), int(top_k)), fetch=True)
        results = []
        for record_id, meta, value in rows:
            score = 1.0 - float(value) if self.metric == "cosine" else -float(value)
            if isinstance(meta, str):
                meta = json.loads(meta)
            results.append(hit(record_id, score, meta))
        return results

    def disconnect(self) -> None:
        """Close the connection if this adapter opened it."""
        if self._conn is not None and self._owns_connection:
            self._conn.close()
        self._conn = None
        self.connected = False

    # -- helpers ------------------------------------------------------------

    def _create_table(self, dimension: int) -> None:
        self._execute(
            f"CREATE TABLE IF NOT EXISTS {self.table} (id TEXT PRIMARY KEY, "
            f"embedding {self._column_type(dimension)}, metadata JSONB NOT NULL DEFAULT '{{}}')"
        )

    def _execute(self, sql: str, params: Optional[tuple] = None, fetch: bool = False):
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall() if fetch else None
        self._conn.commit()
        return rows

    def _require(self) -> None:
        if not self.connected or self._conn is None:
            raise VectorDBNotConnectedError(type(self).__name__)
