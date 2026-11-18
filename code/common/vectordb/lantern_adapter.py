"""Lantern vector database adapter implementation (https://github.com/lanterndata/lantern).

Lantern is a PostgreSQL extension that stores embeddings as ``REAL[]`` and
provides distance functions. This adapter reuses the pgvector adapter and
only changes the column type and the distance SQL:

    cosine  cos_dist(embedding, q)
    l2      sqrt(l2sq_dist(embedding, q))
    ip      not provided by Lantern's distance functions -> configuration error

Not verified against a live Lantern server (only SQL generation is unit
tested); if a Lantern release renames these functions, adjust
``_distance_sql``.

Previously a stub returning a constant score; the class name and the
VectorDBAdapter methods are unchanged.
"""

# Adapters share the same contract and validation steps by design.
# pylint: disable=duplicate-code,too-many-instance-attributes

from typing import Any, Dict, List

from ai_platform.common.vectordb.pgvector_adapter import PGVectorAdapter
from ai_platform.common.vectordb.vector_store_support import VectorDBConfigurationError


class LanternAdapter(PGVectorAdapter):
    """Adapter for PostgreSQL with the Lantern extension."""

    EXTENSION = "lantern"

    def connect(self, config: Dict[str, Any]) -> None:
        """Reject the unsupported metric before connecting."""
        if config.get("metric") == "ip":
            raise VectorDBConfigurationError("lantern: metric 'ip' is not supported")
        super().connect(config)

    def _column_type(self, dimension: int) -> str:
        return "REAL[]"

    def _distance_sql(self) -> str:
        if self.metric == "cosine":
            return "cos_dist(embedding, %s::real[])"
        return "sqrt(l2sq_dist(embedding, %s::real[]))"

    def _value_sql(self) -> str:
        return "%s::real[]"

    def _to_param(self, vector: List[float]) -> Any:
        return [float(x) for x in vector]
