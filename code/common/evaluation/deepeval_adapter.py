"""DeepEval adapter (https://deepeval.com).

Builds one ``LLMTestCase`` per example and runs each configured DeepEval
metric on it with ``metric.measure(test_case)``. DeepEval's metrics are
mostly LLM-as-judge metrics, so they need a judge model configured on the
metric objects themselves (DeepEval's default calls OpenAI).

Configuration:

    metrics_objects   list of DeepEval metric instances (required), e.g.
                      [AnswerRelevancyMetric(threshold=0.7, model=...)]

``evaluate(predictions, references, questions=[...], contexts=[[...], ...])``
- questions become ``input`` (default ""), contexts ``retrieval_context``.

Result: ``{"tool": "DeepEval", "n", "metrics": {name: mean score},
"per_example": {name: [score, ...]}, "passed": {name: fraction passing}}``.
Not verified against an installed DeepEval here (the package was not
installed when this was written). Previously a stub returning constant
metrics; the class name and the EvaluationAdapter methods are unchanged.
"""

from typing import Any, Dict, List

from ai_platform.common.evaluation.base import EvaluationAdapter
from ai_platform.common.evaluation.native_evaluation_adapter import EvaluationError


class DeepEvalAdapter(EvaluationAdapter):
    """Runs DeepEval metrics over predictions and references."""

    TOOL = "DeepEval"

    def __init__(self):
        self.initialized = False
        self._metrics = []
        self._test_case_cls = None

    def initialize(self, config: Dict[str, Any]) -> None:
        """Import DeepEval and take the metric objects."""
        try:
            from deepeval.test_case import LLMTestCase  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise EvaluationError("DeepEvalAdapter requires: pip install deepeval") from exc
        self._metrics = list(config.get("metrics_objects") or [])
        if not self._metrics:
            raise EvaluationError(
                "DeepEvalAdapter needs 'metrics_objects' (DeepEval metric instances)")
        self._test_case_cls = LLMTestCase
        self.initialized = True

    def evaluate(self, predictions: List[Any], references: List[Any], **kwargs) -> Dict[str, Any]:
        """Measure every metric on every example."""
        if not self.initialized:
            raise EvaluationError("DeepEvalAdapter is not initialized")
        n = len(predictions)
        if n != len(references):
            raise EvaluationError(f"{n} predictions but {len(references)} references")
        questions = kwargs.get("questions") or [""] * n
        contexts = kwargs.get("contexts") or [None] * n

        per_example: Dict[str, List[float]] = {}
        passed: Dict[str, int] = {}
        for prediction, reference, question, context in zip(predictions, references,
                                                             questions, contexts):
            case = self._test_case_cls(input=question, actual_output=str(prediction),
                                       expected_output=str(reference),
                                       retrieval_context=context)
            for metric in self._metrics:
                name = getattr(metric, "__name__", type(metric).__name__)
                metric.measure(case)
                per_example.setdefault(name, []).append(float(metric.score))
                passed[name] = passed.get(name, 0) + int(bool(metric.is_successful()))
        return {"tool": self.TOOL, "n": n,
                "metrics": {k: sum(v) / len(v) for k, v in per_example.items()},
                "per_example": per_example,
                "passed": {k: v / n for k, v in passed.items()} if n else {}}

    def shutdown(self) -> None:
        """Drop metric objects."""
        self._metrics = []
        self.initialized = False
