"""Unit tests of retrieval metrics, the retrieval set, the evaluator and its CLI."""

import json

import pytest

from ai_platform.backend.domain_layer.business_logic.rag_benchmark.retrieval_sets import (
    Document,
    Query,
    RetrievalSet,
    RetrievalSetError,
    get_retrieval_set,
)
from ai_platform.backend.service_layer.macro.rag_benchmark.retrieval_evaluator import (
    evaluate_embedders,
)
from ai_platform.backend.ui_layer.cli import rag_benchmark_cli
from ai_platform.common.evaluation import retrieval_metrics as m
from ai_platform.common.rag.embedder import EmbeddingError, HashingEmbedder


def test_metrics():
    assert m.hit_at_k(["a", "b", "c"], ["c"], 2) == 0.0
    assert m.hit_at_k(["a", "b", "c"], ["c"], 3) == 1.0
    assert m.reciprocal_rank(["a", "b"], ["b"]) == 0.5
    assert m.reciprocal_rank(["a"], ["z"]) == 0.0
    assert m.recall_at_k(["a", "b"], ["a", "z"], 2) == 0.5
    agg = m.aggregate_retrieval([m.score_query(["a"], ["a"]), m.score_query(["b", "a"], ["a"])])
    assert agg["mrr"] == pytest.approx(0.75) and agg["hit@1"] == 0.5


def test_builtin_set_and_validation():
    retrieval_set = get_retrieval_set("bilingual_retrieval")
    assert len(retrieval_set.documents) == 12 and len(retrieval_set.queries) == 16
    with pytest.raises(RetrievalSetError):
        RetrievalSet("x", "1", [Document("a", "pl", "t")], [Query("q", "pl", "t", ["b"])])
    with pytest.raises(RetrievalSetError):
        get_retrieval_set("nope")


def test_evaluator_lexical_and_failure():
    tiny = RetrievalSet("t", "1",
                        [Document("cat", "en", "cats are mammals"),
                         Document("car", "en", "cars have engines")],
                        [Query("q1", "en", "are cats mammals", ["cat"]),
                         Query("q2", "en", "engines in cars", ["car"])])

    def factory(name):
        if name == "broken":
            raise EmbeddingError("no server")
        return HashingEmbedder(64)

    report = evaluate_embedders(tiny, ["hashing", "broken"], factory, top_k=2)
    ok, broken = report["results"]
    assert ok["metrics"]["hit@1"] == 1.0 and ok["by_direction"]["en->en"]["mrr"] == 1.0
    assert ok["queries"][0]["ranked"][0] == "cat"
    assert broken["status"] == "FAIL" and broken["error_type"] == "EmbeddingError"


def test_cli_writes_three_files(tmp_path, capsys):
    out = tmp_path / "r.json"
    assert rag_benchmark_cli.main(["run", "--embedders", "hashing:128",
                                   "--output", str(out)]) == 0
    printed = capsys.readouterr().out.split()
    assert printed == [str(out), str(out.with_suffix(".html")), str(out.with_suffix(".md"))]
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["results"][0]["status"] == "PASS"
    assert out.with_suffix(".html").read_text(encoding="utf-8").count("<table>") == 3
