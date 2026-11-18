"""
Shared behaviour of the vector database adapters.

Contract every adapter in this package follows (on top of VectorDBAdapter):

- ``insert(vectors, metadata)``: ``metadata[i]`` belongs to ``vectors[i]``;
  an ``"id"`` key in the metadata is used as the record id, otherwise the
  adapter assigns one (sequential integers, as strings). Returns ``None``
  per the base interface; the ids are available as ``last_insert_ids``.
- ``search(query_vector, top_k)`` returns at most ``top_k`` dicts sorted by
  relevance::

      {"id": str, "score": float, "metadata": dict}

  ``score`` is always "higher is more similar": cosine similarity for
  ``metric="cosine"``, inner product for ``"ip"`` and ``-distance`` for
  ``"l2"``, whatever convention the backend uses natively.
- Methods called before ``connect()`` raise ``VectorDBNotConnectedError``;
  a missing optional SDK raises ``VectorDBDependencyError``.
"""

import math
from typing import Any, Dict, List, Optional, Sequence

METRICS = ("cosine", "l2", "ip")


class VectorDBError(Exception):
    """Base class of vector database adapter errors."""


class VectorDBNotConnectedError(VectorDBError):
    """A method was called before ``connect()`` or after ``disconnect()``."""

    def __init__(self, adapter: str) -> None:
        super().__init__(f"{adapter} is not connected - call connect() first")


class VectorDBConfigurationError(VectorDBError):
    """Invalid configuration or invalid input data."""


class VectorDBDependencyError(VectorDBError):
    """The backend's Python package is not installed."""

    def __init__(self, adapter: str, package: str) -> None:
        super().__init__(f"{adapter} requires the '{package}' package: pip install {package}")
        self.package = package


def check_metric(metric: str) -> str:
    """Validate and return the metric name."""
    if metric not in METRICS:
        raise VectorDBConfigurationError(f"metric must be one of {METRICS}, got {metric!r}")
    return metric


def validate_batch(vectors: Sequence[Sequence[float]], metadata: Sequence[Dict[str, Any]],
                   dimension: Optional[int]) -> int:
    """Check a batch for insert; return its (common) dimension."""
    if len(vectors) != len(metadata):
        raise VectorDBConfigurationError(
            f"{len(vectors)} vectors but {len(metadata)} metadata entries"
        )
    if not vectors:
        return dimension or 0
    dims = {len(v) for v in vectors}
    if len(dims) != 1:
        raise VectorDBConfigurationError(f"vectors have different dimensions: {sorted(dims)}")
    found = dims.pop()
    if dimension and found != dimension:
        raise VectorDBConfigurationError(f"expected dimension {dimension}, got {found}")
    return found


def validate_query(query_vector: Sequence[float], dimension: Optional[int], top_k: int) -> None:
    """Check a query vector and top_k."""
    if top_k < 1:
        raise VectorDBConfigurationError(f"top_k must be >= 1, got {top_k}")
    if dimension and len(query_vector) != dimension:
        raise VectorDBConfigurationError(
            f"query has dimension {len(query_vector)}, index has {dimension}"
        )


def assign_ids(metadata: Sequence[Dict[str, Any]], next_id: int) -> List[str]:
    """Use metadata["id"] where present, else sequential ids from ``next_id``."""
    ids = []
    for offset, meta in enumerate(metadata):
        ids.append(str(meta["id"]) if "id" in meta else str(next_id + offset))
    return ids


def normalize(vector: Sequence[float]) -> List[float]:
    """Return the unit vector (zero vector stays zero)."""
    norm = math.sqrt(sum(x * x for x in vector))
    return [x / norm for x in vector] if norm else list(vector)


def similarity(a: Sequence[float], b: Sequence[float], metric: str) -> float:
    """Score of ``b`` for query ``a``: higher is more similar for every metric."""
    if metric == "ip":
        return sum(x * y for x, y in zip(a, b))
    if metric == "cosine":
        return sum(x * y for x, y in zip(normalize(a), normalize(b)))
    return -math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def score_from_distance(distance: float, metric: str) -> float:
    """Convert a backend distance to a higher-is-better score.

    Backends report cosine as ``1 - cos`` and l2 as either the distance or
    its square; callers pass the plain l2 distance here.
    """
    if metric == "cosine":
        return 1.0 - distance
    if metric == "ip":
        return -distance
    return -distance


def hit(record_id: Any, score: float, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Build one search result in the package-wide shape."""
    return {"id": str(record_id), "score": float(score), "metadata": dict(metadata or {})}
