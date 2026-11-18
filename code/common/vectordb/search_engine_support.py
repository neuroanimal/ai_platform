"""
Shared implementation of the Elasticsearch and OpenSearch adapters.

Both engines are driven through their REST API with the stdlib
``HttpJsonClient``, so no SDK is needed. They differ only in the index
mapping and the k-NN query syntax, which subclasses provide.

Both report a relevance ``_score`` derived from the metric in the same way:

    cosine   (1 + cos) / 2
    l2       1 / (1 + d^2)
    ip       dot + 1 if dot >= 0 else 1 / (1 - dot)

``_to_similarity`` inverts these formulas so that ``score`` follows the
package-wide convention (cosine similarity, inner product, -distance).

Configuration:

    url          e.g. "http://127.0.0.1:9200"
    index        index name (lowercase), default "ai_platform"
    metric       "cosine" (default), "l2" or "ip"
    dimension    optional; otherwise taken from the first insert
    api_key / api_key_env    sent as "Authorization: ApiKey <key>"
    username / password      HTTP basic auth (alternative to api_key)
    timeout      seconds, default 60
"""

# Adapters share the same contract and validation steps by design.
# pylint: disable=duplicate-code,too-many-instance-attributes

import base64
import json
import math
import os
from typing import Any, Dict, List, Optional

from ai_platform.common.util.http_json_client import (
    HttpConnectionError,
    HttpDecodeError,
    HttpJsonClient,
    HttpStatusError,
)
from ai_platform.common.vectordb.base import VectorDBAdapter
from ai_platform.common.vectordb.vector_store_support import (
    VectorDBConfigurationError,
    VectorDBError,
    VectorDBNotConnectedError,
    assign_ids,
    check_metric,
    hit,
    validate_batch,
    validate_query,
)


class SearchEngineVectorAdapter(VectorDBAdapter):
    """Base class for REST search engines with dense-vector k-NN."""

    ENGINE = "search-engine"
    DEFAULT_URL = "http://127.0.0.1:9200"

    def __init__(self):
        self.connected = False
        self.metric = "cosine"
        self.index = "ai_platform"
        self.dimension: Optional[int] = None
        self.last_insert_ids: List[str] = []
        self._client: Optional[HttpJsonClient] = None
        self._count = 0

    # -- subclass hooks -------------------------------------------------

    def _mapping(self, dimension: int) -> Dict[str, Any]:
        raise NotImplementedError

    def _knn_query(self, vector: List[float], top_k: int) -> Dict[str, Any]:
        raise NotImplementedError

    # -- VectorDBAdapter --------------------------------------------------

    def connect(self, config: Dict[str, Any]) -> None:
        """Create the client and read the index dimension if the index exists."""
        self.metric = check_metric(config.get("metric", "cosine"))
        self.index = config.get("index", "ai_platform")
        if self.index != self.index.lower():
            raise VectorDBConfigurationError(f"index names must be lowercase: {self.index!r}")
        self.dimension = config.get("dimension")
        self._client = HttpJsonClient(config.get("url", self.DEFAULT_URL),
                                      timeout=float(config.get("timeout", 60)),
                                      headers=self._auth_headers(config))
        existing = self._existing_dimension()
        if existing:
            self.dimension = existing
            self._count = self._call("GET", f"/{self.index}/_count").get("count", 0)
        elif self.dimension:
            self._create_index(self.dimension)
        self.connected = True

    def insert(self, vectors: List[List[float]], metadata: List[Dict[str, Any]]) -> None:
        """Index documents (replace by id) and refresh so they are searchable."""
        self._require()
        dimension = validate_batch(vectors, metadata, self.dimension)
        if not vectors:
            self.last_insert_ids = []
            return
        if not self.dimension:
            self.dimension = dimension
            self._create_index(dimension)

        ids = assign_ids(metadata, self._count)
        for record_id, vector, meta in zip(ids, vectors, metadata):
            self._call("PUT", f"/{self.index}/_doc/{record_id}", {
                "record_id": record_id,
                "vector": list(map(float, vector)),
                # Stored as text: arbitrary metadata must not change the mapping.
                "metadata_json": json.dumps(meta),
            })
        self._call("POST", f"/{self.index}/_refresh", {})
        self._count += len(ids)
        self.last_insert_ids = ids

    def search(self, query_vector: List[float], top_k: int) -> List[Dict[str, Any]]:
        """k-NN search."""
        self._require()
        validate_query(query_vector, self.dimension, top_k)
        if not self.dimension:
            return []
        answer = self._call("POST", f"/{self.index}/_search",
                            self._knn_query(list(map(float, query_vector)), top_k))
        results = []
        for item in answer.get("hits", {}).get("hits", [])[:top_k]:
            source = item.get("_source") or {}
            results.append(hit(source.get("record_id", item.get("_id")),
                               self._to_similarity(float(item["_score"])),
                               json.loads(source.get("metadata_json") or "{}")))
        return results

    def disconnect(self) -> None:
        """Drop the client (the index stays on the server)."""
        self._client = None
        self.connected = False

    # -- helpers ----------------------------------------------------------

    def _to_similarity(self, score: float) -> float:
        if self.metric == "cosine":
            return 2.0 * score - 1.0
        if self.metric == "l2":
            return -math.sqrt(max(1.0 / score - 1.0, 0.0)) if score > 0 else -math.inf
        return score - 1.0 if score >= 1.0 else 1.0 - 1.0 / score

    @staticmethod
    def _auth_headers(config: Dict[str, Any]) -> Dict[str, str]:
        api_key = config.get("api_key") or os.environ.get(config.get("api_key_env") or "")
        if api_key:
            return {"Authorization": f"ApiKey {api_key}"}
        if config.get("username"):
            token = base64.b64encode(
                f"{config['username']}:{config.get('password', '')}".encode()
            ).decode()
            return {"Authorization": f"Basic {token}"}
        return {}

    def _existing_dimension(self) -> Optional[int]:
        try:
            mapping = self._call("GET", f"/{self.index}/_mapping")
        except VectorDBError as exc:
            if getattr(exc, "status", None) == 404:
                return None
            raise
        props = (mapping.get(self.index, {}).get("mappings", {}).get("properties", {}))
        field = props.get("vector", {})
        return field.get("dims") or field.get("dimension")

    def _create_index(self, dimension: int) -> None:
        self._call("PUT", f"/{self.index}", self._mapping(dimension))

    def _call(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None):
        try:
            return self._client.request(method, path, payload).data or {}
        except HttpStatusError as exc:
            error = VectorDBError(f"{self.ENGINE}: {exc}")
            error.status = exc.status
            raise error from exc
        except (HttpConnectionError, HttpDecodeError) as exc:
            raise VectorDBError(f"{self.ENGINE}: {exc}") from exc

    def _require(self) -> None:
        if not self.connected or self._client is None:
            raise VectorDBNotConnectedError(type(self).__name__)
