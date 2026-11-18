"""Tests of the evaluation metrics and adapters.

Native metrics, MLflow (local sqlite store) and TensorBoard (event files)
run for real in a temporary directory. LangSmith, W&B, HF evaluate,
DeepEval and RAGAS run against fakes: they prove the wiring, not the
compatibility with a real release or service.
"""

import importlib.util
import math
import sys
import types

import pytest

from ai_platform.common.evaluation import metrics as m
from ai_platform.common.evaluation.deepeval_adapter import DeepEvalAdapter
from ai_platform.common.evaluation.hf_evaluate_adapter import HFEvaluateAdapter
from ai_platform.common.evaluation.humanloop_adapter import HumanLoopAdapter
from ai_platform.common.evaluation.langsmith_adapter import LangSmithAdapter
from ai_platform.common.evaluation.mirascope_adapter import MiraScopeAdapter
from ai_platform.common.evaluation.mlflow_adapter import MLflowAdapter
from ai_platform.common.evaluation.native_evaluation_adapter import (
    EvaluationError,
    NativeEvaluationAdapter,
    parse_judge_score,
)
from ai_platform.common.evaluation.ragas_adapter import RAGASAdapter
from ai_platform.common.evaluation.tensorboard_adapter import TensorBoardAdapter
from ai_platform.common.evaluation.trulens_adapter import TrulensAdapter
from ai_platform.common.evaluation.wandb_adapter import WandBAdapter
from ai_platform.common.llm.chat_result import ChatResult

PRED = ["17 razy 23 to 391.", "Nie, Mruczek nie jest ssakiem.", "Wzrost o 12,0%"]
REF = ["391", "Tak, Mruczek jest ssakiem.", "12%"]


# ----------------------------------------------------------------------------
# metrics
# ----------------------------------------------------------------------------

def test_normalization_handles_polish_and_decimal_comma():
    assert m.normalize_text("Wzrost o 12,5%!") == "wzrost o 12.5"
    assert m.normalize_text("„Tak”, Mruczek.") == "tak mruczek"


@pytest.mark.parametrize("pred,ref,metric,expected", [
    ("Tak, Mruczek jest ssakiem.", "tak mruczek jest ssakiem", "exact_match", 1.0),
    ("Odpowiedź: 391", "391", "exact_match", 0.0),
    ("Odpowiedź: 391", "391", "contains", 1.0),
    ("17 razy 23 to 391", "391", "numeric_match", 1.0),
    ("17 razy 23 to 85", "391", "numeric_match", 0.0),
    ("12,0%", "12%", "numeric_match", 1.0),
    ("a b c", "a b c", "token_f1", 1.0),
    ("a b", "c d", "token_f1", 0.0),
    ("a x b y c", "a b c", "rouge_l", 0.75),
])
def test_metric_values(pred, ref, metric, expected):
    assert m.METRICS[metric](pred, ref) == pytest.approx(expected)


def test_compute_validates_lengths_and_names():
    with pytest.raises(ValueError):
        m.compute(["a"], [])
    with pytest.raises(ValueError):
        m.compute(["a"], ["a"], ["bleu"])


# ----------------------------------------------------------------------------
# native adapter and judge
# ----------------------------------------------------------------------------

class Judge:
    """Scripted judge LLM."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.prompts = []

    def chat_completion(self, messages, **kwargs):
        """Reply with the next scripted answer."""
        assert kwargs["temperature"] == 0
        self.prompts.append(messages[0]["content"])
        return ChatResult(text=self.replies.pop(0), model="judge")


def test_native_evaluation_and_judge():
    judge = Judge(["1", "Score: 0", "nie wiem"])
    ev = NativeEvaluationAdapter()
    ev.initialize({"metrics": ["numeric_match", "contains"], "judge": judge})
    result = ev.evaluate(PRED, REF, questions=["q1", "q2", "q3"])
    assert result["metrics"]["numeric_match"] == pytest.approx(2 / 3)
    assert result["per_example"]["judge_score"] == [1.0, 0.0, None]
    assert result["metrics"]["judge_score"] == pytest.approx(0.5)
    assert result["metrics"]["judge_unparsed"] == 1.0
    assert "QUESTION: q2" in judge.prompts[1]


@pytest.mark.parametrize("reply,score", [("0.8", 0.8), ("1", 1.0), ("Ocena: 0,5", 0.5),
                                         ("7", None), ("", None)])
def test_parse_judge_score(reply, score):
    assert parse_judge_score(reply) == score


def test_native_errors():
    ev = NativeEvaluationAdapter()
    with pytest.raises(EvaluationError):
        ev.evaluate(["a"], ["a"])
    with pytest.raises(EvaluationError):
        ev.initialize({"metrics": ["nope"]})


# ----------------------------------------------------------------------------
# MLflow and TensorBoard (real)
# ----------------------------------------------------------------------------

@pytest.mark.skipif(not importlib.util.find_spec("mlflow"), reason="mlflow not installed")
def test_mlflow_logs_metrics(tmp_path):
    import mlflow  # pylint: disable=import-outside-toplevel
    uri = f"sqlite:///{tmp_path}/mlflow.db"
    ev = MLflowAdapter()
    ev.initialize({"tracking_uri": uri, "experiment_name": "t", "metrics": ["numeric_match"],
                   "artifact_location": str(tmp_path / "artifacts")})
    result = ev.evaluate(PRED, REF, run_name="unit")
    ev.shutdown()
    run = mlflow.MlflowClient(tracking_uri=uri).get_run(result["run_id"])
    assert run.data.metrics["numeric_match"] == pytest.approx(2 / 3)
    assert run.data.params["n_examples"] == "3"


@pytest.mark.skipif(not importlib.util.find_spec("torch"), reason="torch not installed")
def test_tensorboard_writes_scalars(tmp_path):
    from tensorboard.backend.event_processing.event_accumulator import (  # pylint: disable=import-outside-toplevel
        EventAccumulator,
    )
    ev = TensorBoardAdapter()
    ev.initialize({"log_dir": str(tmp_path), "metrics": ["contains"]})
    ev.evaluate(PRED, REF)
    ev.evaluate(PRED[:1], REF[:1])
    ev.shutdown()
    acc = EventAccumulator(str(tmp_path))
    acc.Reload()
    values = [e.value for e in acc.Scalars("eval/contains")]
    assert values == pytest.approx([2 / 3, 1.0])


# ----------------------------------------------------------------------------
# fakes
# ----------------------------------------------------------------------------

def test_langsmith_feedback_only_with_run_id():
    calls = []
    client = types.SimpleNamespace(create_feedback=lambda run_id, **kw: calls.append((run_id, kw)))
    ev = LangSmithAdapter()
    ev.initialize({"client": client, "metrics": ["contains"]})
    assert ev.evaluate(PRED, REF)["logged"] is False
    assert ev.evaluate(PRED, REF, run_id="r1")["logged"] is True
    assert calls == [("r1", {"key": "contains", "score": pytest.approx(2 / 3),
                             "comment": "ai_platform, n=3"})]


def test_wandb_with_fake_module(monkeypatch):
    logged = []
    run = types.SimpleNamespace(id="w1", settings=types.SimpleNamespace(mode="offline"),
                                log=logged.append, finish=lambda: None)
    fake = types.SimpleNamespace(init=lambda **kw: run,
                                 Table=lambda columns, data: {"columns": columns, "data": data})
    monkeypatch.setitem(sys.modules, "wandb", fake)
    ev = WandBAdapter()
    ev.initialize({"metrics": ["contains"]})
    result = ev.evaluate(PRED, REF)
    ev.shutdown()
    assert result["run_id"] == "w1"
    assert logged[0]["contains"] == pytest.approx(2 / 3)
    assert logged[0]["per_example"]["columns"] == ["contains"]


def test_hf_evaluate_with_fake_module(monkeypatch):
    class Metric:
        """Fake evaluate metric."""
        def compute(self, predictions, references):
            """Exact match."""
            hits = sum(p == r for p, r in zip(predictions, references))
            return {"exact_match": hits / len(predictions), "details": [1, 2]}

    monkeypatch.setitem(sys.modules, "evaluate", types.SimpleNamespace(load=lambda name: Metric()))
    ev = HFEvaluateAdapter()
    ev.initialize({"hf_metrics": ["exact_match"]})
    result = ev.evaluate(["a", "b"], ["a", "c"])
    assert result["metrics"] == {"exact_match.exact_match": 0.5}
    assert result["raw"] == {"exact_match.details": [1, 2]}


def test_deepeval_with_fake_module(monkeypatch):
    class LLMTestCase:
        """Fake test case."""
        def __init__(self, **kw):
            self.__dict__.update(kw)

    class Metric:
        """Fake metric: 1 if expected text is contained."""
        __name__ = "Contains"

        def __init__(self):
            self.score = 0.0

        def measure(self, case):
            """Score."""
            self.score = float(case.expected_output in case.actual_output)

        def is_successful(self):
            """Pass if score is 1."""
            return self.score == 1.0

    monkeypatch.setitem(sys.modules, "deepeval", types.ModuleType("deepeval"))
    monkeypatch.setitem(sys.modules, "deepeval.test_case",
                        types.SimpleNamespace(LLMTestCase=LLMTestCase))
    ev = DeepEvalAdapter()
    ev.initialize({"metrics_objects": [Metric()]})
    result = ev.evaluate(["x 391", "85"], ["391", "391"])
    assert result["metrics"]["Contains"] == 0.5
    assert result["passed"]["Contains"] == 0.5
    with pytest.raises(EvaluationError):
        DeepEvalAdapter().initialize({})


def test_ragas_with_fake_module(monkeypatch):
    class Frame:
        """Fake pandas frame."""
        def __init__(self, data):
            self.data = data
            self.columns = list(data)

        def __getitem__(self, key):
            return types.SimpleNamespace(tolist=lambda: self.data[key])

    captured = {}

    def evaluate(dataset, metrics, **kw):
        captured.update(dataset=dataset, metrics=metrics, kw=kw)
        return types.SimpleNamespace(to_pandas=lambda: Frame({
            "user_input": ["q1", "q2"], "faithfulness": [1.0, math.nan]}))

    fake = types.SimpleNamespace(
        EvaluationDataset=types.SimpleNamespace(from_list=lambda samples: samples),
        evaluate=evaluate)
    monkeypatch.setitem(sys.modules, "ragas", fake)
    ev = RAGASAdapter()
    ev.initialize({"metrics_objects": ["faithfulness"], "llm": "judge"})
    result = ev.evaluate(["a", "b"], ["a", "c"], questions=["q1", "q2"], contexts=[["c1"], []])
    assert captured["dataset"][0] == {"user_input": "q1", "response": "a", "reference": "a",
                                      "retrieved_contexts": ["c1"]}
    assert captured["kw"] == {"llm": "judge"}
    assert result["metrics"] == {"faithfulness": 1.0}


@pytest.mark.parametrize("cls", [TrulensAdapter, HumanLoopAdapter, MiraScopeAdapter])
def test_refusing_adapters(cls):
    with pytest.raises(NotImplementedError, match="instead"):
        cls().initialize({})
    with pytest.raises(NotImplementedError):
        cls().evaluate(["a"], ["a"])
