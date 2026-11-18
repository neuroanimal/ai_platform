"""Tests of the vector DB adapters that need a server or an absent SDK.

- Elasticsearch / OpenSearch / Pinecone / Weaviate run against an
  in-process fake server that implements just enough of each REST API
  (including the engine's own score formula), so the score conversion is
  checked end to end.
- pgvector / Lantern run against a fake DB-API connection that records SQL.
- Milvus / LanceDB / txtai run against fake clients or fake modules.

None of this proves compatibility with a real server release; the live
check for those backends is still open.
"""

import json
import math
import os
import re
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(__file__))

from fake_json_server import FakeJsonServer  # noqa: E402

from ai_platform.common.vectordb.elasticsearch_adapter import ElasticsearchAdapter  # noqa: E402
from ai_platform.common.vectordb.lancedb_adapter import LanceDBAdapter  # noqa: E402
from ai_platform.common.vectordb.lantern_adapter import LanternAdapter  # noqa: E402
from ai_platform.common.vectordb.milvus_adapter import MilvusAdapter  # noqa: E402
from ai_platform.common.vectordb.opensearch_adapter import OpenSearchAdapter  # noqa: E402
from ai_platform.common.vectordb.pgvector_adapter import PGVectorAdapter  # noqa: E402
from ai_platform.common.vectordb.pinecone_adapter import PineconeAdapter  # noqa: E402
from ai_platform.common.vectordb.txtai_adapter import TXTaiAdapter  # noqa: E402
from ai_platform.common.vectordb.vector_store_support import (  # noqa: E402
    VectorDBConfigurationError,
    VectorDBDependencyError,
)
from ai_platform.common.vectordb.weaviate_adapter import WeaviateAdapter  # noqa: E402

VECTORS = [[1.0, 0.0], [0.0, 1.0], [0.8, 0.6]]
META = [{"id": "a", "k": 1}, {"id": "b"}, {"id": "c"}]
QUERY = [1.0, 0.1]


def cos(a, b):
    """Cosine similarity."""
    return sum(x * y for x, y in zip(a, b)) / (math.hypot(*a) * math.hypot(*b))


def l2(a, b):
    """Euclidean distance."""
    return math.dist(a, b)


def expected_order(metric):
    """Ids sorted by true similarity to QUERY."""
    key = {"cosine": lambda v: cos(QUERY, v), "l2": lambda v: -l2(QUERY, v),
           "ip": lambda v: sum(x * y for x, y in zip(QUERY, v))}[metric]
    return [m["id"] for _, m in sorted(zip(VECTORS, META), key=lambda p: -key(p[0]))]


# ----------------------------------------------------------------------------
# Elasticsearch / OpenSearch fake
# ----------------------------------------------------------------------------

def search_engine_routes(store, index, engine):
    """Fake ES/OpenSearch REST API with the engines' score formulas."""

    def mapping(method, _path, body, _h):
        if method == "PUT":
            store["mapping"] = body
            return 200, {"acknowledged": True}
        if "mapping" not in store:
            return 404, {"error": "index_not_found_exception"}
        return 200, {index: store["mapping"]}

    def doc(_m, path, body, _h):
        store.setdefault("docs", {})[path.rsplit("/", 1)[1]] = body
        return 201, {"result": "created"}

    def search(_m, _p, body, _h):
        field = store["mapping"]["mappings"]["properties"]["vector"]
        if engine == "es":
            metric, query, k = field["similarity"], body["knn"]["query_vector"], body["knn"]["k"]
        else:
            metric = field["method"]["space_type"]
            query, k = body["query"]["knn"]["vector"]["vector"], body["query"]["knn"]["vector"]["k"]
        hits = []
        for doc_id, source in store.get("docs", {}).items():
            vec = source["vector"]
            if metric in ("cosine", "cosinesimil"):
                score = (1 + cos(query, vec)) / 2
            elif metric in ("l2_norm", "l2"):
                score = 1 / (1 + l2(query, vec) ** 2)
            else:
                dot = sum(x * y for x, y in zip(query, vec))
                score = dot + 1 if dot >= 0 else 1 / (1 - dot)
            hits.append({"_id": doc_id, "_score": score, "_source": source})
        hits.sort(key=lambda h: -h["_score"])
        return 200, {"hits": {"hits": hits[:k]}}

    routes = {("GET", f"/{index}/_mapping"): mapping, ("PUT", f"/{index}"): mapping,
              ("POST", f"/{index}/_refresh"): {"ok": True},
              ("POST", f"/{index}/_search"): search,
              ("GET", f"/{index}/_count"): lambda *a: (200, {"count": len(store.get("docs", {}))})}
    for meta in META + [{"id": "0"}, {"id": "1"}]:
        routes[("PUT", f"/{index}/_doc/{meta['id']}")] = doc
    return routes


@pytest.mark.parametrize("cls,engine", [(ElasticsearchAdapter, "es"), (OpenSearchAdapter, "os")])
@pytest.mark.parametrize("metric", ["cosine", "l2", "ip"])
def test_search_engines_roundtrip_and_score_conversion(cls, engine, metric):
    store = {}
    with FakeJsonServer(search_engine_routes(store, "idx", engine)) as server:
        db = cls()
        db.connect({"url": server.url, "index": "idx", "metric": metric, "api_key": "k"})
        db.insert(VECTORS, META)
        results = db.search(QUERY, top_k=3)
        db.disconnect()
    assert [r["id"] for r in results] == expected_order(metric)
    assert results[0]["metadata"] == {"id": "a", "k": 1}
    if metric == "cosine":
        assert results[0]["score"] == pytest.approx(cos(QUERY, [1.0, 0.0]))
    if metric == "l2":
        assert results[0]["score"] == pytest.approx(-l2(QUERY, [1.0, 0.0]))
    assert server.requests[0]["headers"]["authorization"] == "ApiKey k"


def test_search_engine_index_name_must_be_lowercase():
    with pytest.raises(VectorDBConfigurationError):
        ElasticsearchAdapter().connect({"index": "Bad"})


# ----------------------------------------------------------------------------
# Pinecone fake
# ----------------------------------------------------------------------------

def test_pinecone_upsert_query_and_auth():
    store = {}

    def upsert(_m, _p, body, headers):
        assert headers["api-key"] == "k"
        for record in body["vectors"]:
            store[record["id"]] = record
        return 200, {"upsertedCount": len(body["vectors"])}

    def query(_m, _p, body, _h):
        matches = sorted(({"id": r["id"], "score": cos(body["vector"], r["values"]),
                           "metadata": r["metadata"]} for r in store.values()),
                         key=lambda m: -m["score"])
        return 200, {"matches": matches[:body["topK"]]}

    routes = {("POST", "/describe_index_stats"): {"dimension": 2, "namespaces": {}},
              ("POST", "/vectors/upsert"): upsert, ("POST", "/query"): query}
    with FakeJsonServer(routes) as server:
        db = PineconeAdapter()
        db.connect({"host": server.url, "api_key": "k"})
        db.insert(VECTORS, META)
        results = db.search(QUERY, top_k=2)
    assert [r["id"] for r in results] == expected_order("cosine")[:2]
    assert "id" not in store["a"]["metadata"]


def test_pinecone_requires_host_and_key(monkeypatch):
    monkeypatch.delenv("PINECONE_API_KEY", raising=False)
    with pytest.raises(VectorDBConfigurationError):
        PineconeAdapter().connect({"api_key": "k"})
    with pytest.raises(VectorDBConfigurationError):
        PineconeAdapter().connect({"host": "x"})


# ----------------------------------------------------------------------------
# Weaviate fake
# ----------------------------------------------------------------------------

def test_weaviate_schema_batch_and_graphql():
    store = {"objects": []}

    def schema_get(*_):
        return (200, {"class": "Docs"}) if "schema" in store else (404, {"error": []})

    def schema_post(_m, _p, body, _h):
        store["schema"] = body
        return 200, body

    def batch(_m, _p, body, _h):
        store["objects"].extend(body["objects"])
        return 200, [{"result": {}} for _ in body["objects"]]

    def graphql(_m, _p, body, _h):
        vector = [float(x) for x in re.search(r"vector: \[([^\]]*)\]", body["query"])
                  .group(1).split(",")]
        limit = int(re.search(r"limit: (\d+)", body["query"]).group(1))
        items = sorted(({**o["properties"], "_additional": {"distance": 1 - cos(vector, o["vector"])}}
                        for o in store["objects"]), key=lambda i: i["_additional"]["distance"])
        return 200, {"data": {"Get": {"Docs": items[:limit]}}}

    routes = {("GET", "/v1/schema/Docs"): schema_get, ("POST", "/v1/schema"): schema_post,
              ("POST", "/v1/batch/objects"): batch, ("POST", "/v1/graphql"): graphql}
    with FakeJsonServer(routes) as server:
        db = WeaviateAdapter()
        db.connect({"url": server.url, "collection": "docs"})
        db.insert(VECTORS, META)
        results = db.search(QUERY, top_k=3)
    assert store["schema"]["vectorizer"] == "none"
    assert [r["id"] for r in results] == expected_order("cosine")
    assert results[0]["score"] == pytest.approx(cos(QUERY, [1.0, 0.0]))


# ----------------------------------------------------------------------------
# pgvector / Lantern fake connection
# ----------------------------------------------------------------------------

class FakeCursor:
    """Records SQL; answers COUNT and SELECT with scripted rows."""

    def __init__(self, conn):
        self.conn = conn
        self._rows = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        """Record and script."""
        self.conn.statements.append((sql, params))
        if sql.startswith("SELECT COUNT"):
            self._rows = [(0,)]
        elif sql.startswith("SELECT id"):
            self._rows = self.conn.select_rows

    def executemany(self, sql, seq):
        """Record a batch."""
        self.conn.statements.append((sql, list(seq)))

    def fetchall(self):
        """Return scripted rows."""
        return self._rows


class FakeConnection:
    """Minimal DB-API connection."""

    def __init__(self, select_rows):
        self.statements = []
        self.select_rows = select_rows
        self.commits = 0

    def cursor(self):
        """New fake cursor."""
        return FakeCursor(self)

    def commit(self):
        """Count commits."""
        self.commits += 1

    def close(self):
        """Not expected: the adapter must not close a connection it did not open."""
        raise AssertionError("adapter closed a borrowed connection")


def test_pgvector_sql_parameters_and_scores():
    conn = FakeConnection([("a", {"k": 1}, 0.1), ("c", json.dumps({}), 0.3)])
    db = PGVectorAdapter()
    db.connect({"connection": conn, "table": "vecs"})
    db.insert(VECTORS, META)
    results = db.search(QUERY, top_k=2)
    db.disconnect()

    sqls = [s for s, _ in conn.statements]
    assert sqls[0] == "CREATE EXTENSION IF NOT EXISTS vector"
    assert any("embedding vector(2)" in s for s in sqls)
    insert_sql, rows = next((s, p) for s, p in conn.statements if s.startswith("INSERT"))
    assert "%s::vector" in insert_sql and rows[0][1] == "[1.0,0.0]"
    select_sql, params = conn.statements[-1]
    assert "embedding <=> %s::vector" in select_sql and params[1] == 2
    assert results[0] == {"id": "a", "score": pytest.approx(0.9), "metadata": {"k": 1}}


def test_pgvector_rejects_bad_table_name():
    with pytest.raises(VectorDBConfigurationError):
        PGVectorAdapter().connect({"connection": FakeConnection([]), "table": "t;drop"})


def test_lantern_sql_and_unsupported_ip():
    conn = FakeConnection([("a", {}, 0.2)])
    db = LanternAdapter()
    db.connect({"connection": conn, "metric": "l2", "dimension": 2})
    db.search(QUERY, top_k=1)
    sqls = [s for s, _ in conn.statements]
    assert sqls[0] == "CREATE EXTENSION IF NOT EXISTS lantern"
    assert any("embedding REAL[]" in s for s in sqls)
    assert "sqrt(l2sq_dist(embedding, %s::real[]))" in sqls[-1]
    with pytest.raises(VectorDBConfigurationError):
        LanternAdapter().connect({"connection": conn, "metric": "ip"})


def test_pgvector_without_psycopg_or_dsn(monkeypatch):
    monkeypatch.setitem(sys.modules, "psycopg", None)
    with pytest.raises(VectorDBDependencyError):
        PGVectorAdapter().connect({"dsn": "postgresql://x"})


# ----------------------------------------------------------------------------
# Milvus fake client
# ----------------------------------------------------------------------------

class FakeMilvusClient:
    """Implements the MilvusClient calls the adapter uses, with real COSINE math."""

    def __init__(self):
        self.collections = {}

    def has_collection(self, name):
        """Exists?"""
        return name in self.collections

    def get_collection_stats(self, name):
        """Row count."""
        return {"row_count": len(self.collections[name]["rows"])}

    def create_collection(self, collection_name, **kwargs):
        """Create."""
        self.collections[collection_name] = {"spec": kwargs, "rows": {}}

    def upsert(self, collection_name, data):
        """Upsert by id."""
        for row in data:
            self.collections[collection_name]["rows"][row["id"]] = row

    def search(self, collection_name, data, limit, output_fields):
        """Brute-force COSINE search."""
        assert output_fields == ["*"]
        rows = self.collections[collection_name]["rows"].values()
        hits = sorted(({"id": r["id"], "distance": cos(data[0], r["vector"]), "entity": dict(r)}
                       for r in rows), key=lambda h: -h["distance"])
        return [hits[:limit]]


def test_milvus_with_fake_client():
    client = FakeMilvusClient()
    db = MilvusAdapter()
    db.connect({"client": client})
    db.insert(VECTORS, META)
    results = db.search(QUERY, top_k=2)
    spec = client.collections["ai_platform"]["spec"]
    assert spec["metric_type"] == "COSINE" and spec["id_type"] == "string"
    assert [r["id"] for r in results] == expected_order("cosine")[:2]
    assert results[0]["metadata"] == {"k": 1}


# ----------------------------------------------------------------------------
# LanceDB and txtai fake modules
# ----------------------------------------------------------------------------

def fake_lancedb_module():
    """Fake 'lancedb' with an in-memory table supporting the query chain."""
    class Query:
        """search() chain."""
        def __init__(self, table, vector):
            self.table, self.vector, self.k, self.kind = table, vector, 10, None

        def distance_type(self, kind):
            """Set distance."""
            self.kind = kind
            return self

        def limit(self, k):
            """Set limit."""
            self.k = k
            return self

        def to_list(self):
            """Execute (cosine only)."""
            assert self.kind == "cosine"
            rows = [dict(r, _distance=1 - cos(self.vector, r["vector"])) for r in self.table.rows]
            return sorted(rows, key=lambda r: r["_distance"])[:self.k]

    class Table:
        """In-memory table."""
        def __init__(self, rows):
            self.rows = list(rows)
            self.schema = types.SimpleNamespace(field=lambda name: types.SimpleNamespace(
                type=types.SimpleNamespace(list_size=len(self.rows[0]["vector"]))))

        def add(self, rows):
            """Append."""
            self.rows.extend(rows)

        def count_rows(self):
            """Count."""
            return len(self.rows)

        def search(self, vector):
            """Start a query."""
            return Query(self, vector)

    class Db:
        """In-memory database."""
        def __init__(self):
            self.tables = {}

        def table_names(self):
            """Names."""
            return list(self.tables)

        def open_table(self, name):
            """Open."""
            return self.tables[name]

        def create_table(self, name, data):
            """Create."""
            self.tables[name] = Table(data)
            return self.tables[name]

    module = types.ModuleType("lancedb")
    module.connect = lambda path: Db()
    return module


def test_lancedb_with_fake_module(monkeypatch):
    monkeypatch.setitem(sys.modules, "lancedb", fake_lancedb_module())
    db = LanceDBAdapter()
    db.connect({"path": "/nonexistent-not-used"})
    db.insert(VECTORS[:2], META[:2])
    db.insert(VECTORS[2:], META[2:])
    results = db.search(QUERY, top_k=3)
    assert [r["id"] for r in results] == expected_order("cosine")
    assert results[0]["score"] == pytest.approx(cos(QUERY, [1.0, 0.0]))


def test_txtai_with_fake_module(monkeypatch):
    class Embeddings:
        """Fake txtai Embeddings: identity transform + exact inner product."""
        def __init__(self, config):
            assert config["transform"]([1, 2]) == [1, 2]
            self.rows = []

        def index(self, rows):
            """Replace the index."""
            self.rows = [(position, list(vector)) for position, vector, _ in rows]

        def search(self, query, limit):
            """Inner product search on (already normalized) vectors."""
            scored = [(p, float(sum(a * b for a, b in zip(query, v)))) for p, v in self.rows]
            return sorted(scored, key=lambda s: -s[1])[:limit]

    monkeypatch.setitem(sys.modules, "txtai", types.SimpleNamespace(Embeddings=Embeddings))
    db = TXTaiAdapter()
    db.connect({})
    db.insert(VECTORS, META)
    results = db.search(QUERY, top_k=3)
    assert [r["id"] for r in results] == expected_order("cosine")
    assert results[0]["score"] == pytest.approx(cos(QUERY, [1.0, 0.0]), abs=1e-6)
    with pytest.raises(VectorDBConfigurationError):
        TXTaiAdapter().connect({"metric": "l2"})
