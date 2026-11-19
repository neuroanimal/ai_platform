"""Behavioural tests of the vector DB adapters that run fully in-process.

The same scenario runs against every local backend (SQLite, FAISS, Chroma,
Qdrant local mode), so the package-wide contract from
vector_store_support.py - result shape, higher-is-better score, id
handling, errors - is checked uniformly. Backends whose package is not
installed are skipped.
"""

import importlib.util
import uuid

import pytest

from ai_platform.common.vectordb.chromadb_adapter import ChromaDBAdapter
from ai_platform.common.vectordb.faiss_adapter import FAISSAdapter
from ai_platform.common.vectordb.qdrant_adapter import QdrantAdapter
from ai_platform.common.vectordb.sqlite_adapter import SQLiteAdapter
from ai_platform.common.vectordb.vector_store_support import (
    VectorDBConfigurationError,
    VectorDBNotConnectedError,
)

BACKENDS = [
    pytest.param(SQLiteAdapter, {}, id="sqlite"),
    pytest.param(FAISSAdapter, {}, id="faiss",
                 marks=pytest.mark.skipif(not importlib.util.find_spec("faiss"),
                                          reason="faiss not installed")),
    pytest.param(ChromaDBAdapter, {}, id="chromadb",
                 marks=pytest.mark.skipif(not importlib.util.find_spec("chromadb"),
                                          reason="chromadb not installed")),
    pytest.param(QdrantAdapter, {}, id="qdrant",
                 marks=pytest.mark.skipif(not importlib.util.find_spec("qdrant_client"),
                                          reason="qdrant-client not installed")),
]

VECTORS = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.9, 0.1, 0.0], [0.0, 0.0, 1.0]]
META = [{"id": "a", "t": "x"}, {"id": "b"}, {"id": "c", "t": "near-a"}, {"id": "d"}]


def connected(cls, extra, metric="cosine", **config):
    """Connect a fresh adapter with a unique collection name.

    Chroma's EphemeralClient is shared per process, so a reused name would
    see the data of an earlier test.
    """
    db = cls()
    db.connect({"metric": metric, "collection": f"t_{metric}_{uuid.uuid4().hex[:12]}",
                **extra, **config})
    return db


@pytest.mark.parametrize("cls,extra", BACKENDS)
@pytest.mark.parametrize("metric", ["cosine", "l2", "ip"])
def test_nearest_neighbours_and_score_order(cls, extra, metric):
    db = connected(cls, extra, metric)
    db.insert(VECTORS, META)
    results = db.search([1.0, 0.05, 0.0], top_k=2)
    db.disconnect()

    assert [r["id"] for r in results] == ["a", "c"]
    assert results[0]["score"] >= results[1]["score"]
    assert results[0]["metadata"]["t"] == "x"
    assert set(results[0]) == {"id", "score", "metadata"}


@pytest.mark.parametrize("cls,extra", BACKENDS)
def test_cosine_score_is_similarity(cls, extra):
    db = connected(cls, extra)
    db.insert([[2.0, 0.0]], [{"id": "same-direction"}])
    (best,) = db.search([1.0, 0.0], top_k=5)
    db.disconnect()
    assert best["score"] == pytest.approx(1.0, abs=1e-4)


@pytest.mark.parametrize("cls,extra", BACKENDS)
def test_generated_ids_and_top_k_bound(cls, extra):
    db = connected(cls, extra)
    db.insert([[1.0, 0.0], [0.0, 1.0]], [{}, {}])
    assert db.last_insert_ids == ["0", "1"]
    assert len(db.search([1.0, 0.0], top_k=10)) == 2
    db.disconnect()


@pytest.mark.parametrize("cls,extra", BACKENDS)
def test_validation_errors(cls, extra):
    db = connected(cls, extra)
    with pytest.raises(VectorDBConfigurationError):
        db.insert([[1.0, 0.0]], [])
    with pytest.raises(VectorDBConfigurationError):
        db.insert([[1.0, 0.0], [1.0]], [{}, {}])
    with pytest.raises(VectorDBConfigurationError):
        db.search([1.0], top_k=0)
    db.disconnect()


@pytest.mark.parametrize("cls,extra", BACKENDS)
def test_not_connected(cls, extra):
    db = cls()
    with pytest.raises(VectorDBNotConnectedError):
        db.search([1.0], 1)
    with pytest.raises(VectorDBNotConnectedError):
        db.insert([[1.0]], [{}])
    del extra


@pytest.mark.parametrize("cls,extra", BACKENDS)
def test_empty_store_returns_nothing(cls, extra):
    db = connected(cls, extra, dimension=2)
    assert not db.search([1.0, 0.0], top_k=3)
    db.disconnect()


def test_sqlite_rejects_sql_identifier_injection():
    with pytest.raises(VectorDBConfigurationError):
        SQLiteAdapter().connect({"table": "x; DROP TABLE y"})


@pytest.mark.skipif(not importlib.util.find_spec("faiss"), reason="faiss not installed")
def test_faiss_persistence_roundtrip(tmp_path):
    path = str(tmp_path / "index.faiss")
    db = FAISSAdapter()
    db.connect({"path": path})
    db.insert(VECTORS, META)
    db.disconnect()

    again = FAISSAdapter()
    again.connect({"path": path})
    assert again.search([0.0, 0.0, 1.0], top_k=1)[0]["id"] == "d"
    again.disconnect()


def test_sqlite_persistence_and_replace_by_id(tmp_path):
    path = str(tmp_path / "v.db")
    db = SQLiteAdapter()
    db.connect({"path": path})
    db.insert([[1.0, 0.0]], [{"id": "k", "v": 1}])
    db.insert([[0.0, 1.0]], [{"id": "k", "v": 2}])
    db.disconnect()

    again = SQLiteAdapter()
    again.connect({"path": path})
    results = again.search([0.0, 1.0], top_k=5)
    again.disconnect()
    assert len(results) == 1
    assert results[0]["metadata"]["v"] == 2
