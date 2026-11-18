"""
Native evaluation adapter: reference metrics plus an optional LLM judge.

``evaluate(predictions, references)`` returns::

    {"tool": "native", "n": int,
     "metrics": {"exact_match": float, ...},        # batch means
     "per_example": {"exact_match": [float, ...], ...}}

Configuration:

    metrics   names from ``metrics.METRICS`` (default: all)
    judge     an LLM adapter with ``chat_completion`` - adds "judge_score",
              the judge's 0..1 rating of each prediction against its
              reference. Answers that cannot be parsed are recorded as None
              and excluded from the mean (count in "judge_unparsed").
    judge_max_tokens   default 8

The tracking-tool adapters (MLflow, TensorBoard, W&B, LangSmith) subclass
this and add their logging step, so the numbers they log are the same.
"""

import re
from typing import Any, Dict, List, Optional

from ai_platform.common.evaluation import metrics as text_metrics
from ai_platform.common.evaluation.base import EvaluationAdapter

JUDGE_PROMPT = (
    "Rate how well the ANSWER matches the REFERENCE in meaning, from 0 "
    "(wrong or unrelated) to 1 (fully correct). Reply with one number only.\n\n"
    "QUESTION: {question}\nREFERENCE: {reference}\nANSWER: {prediction}\nSCORE:"
)
_FIRST_NUMBER = re.compile(r"(?<![\d.])(0(?:\.\d+)?|1(?:\.0+)?)(?![\d])")


class EvaluationError(Exception):
    """Evaluation misuse or failure."""


def parse_judge_score(text: str) -> Optional[float]:
    """First number in [0, 1] in the judge's reply, else None."""
    match = _FIRST_NUMBER.search(str(text or "").replace(",", "."))
    return float(match.group(1)) if match else None


class NativeEvaluationAdapter(EvaluationAdapter):
    """Computes metrics in-process; base of the tracking-tool adapters."""

    TOOL = "native"

    def __init__(self) -> None:
        self.initialized = False
        self.metric_names: List[str] = list(text_metrics.METRICS)
        self.judge = None
        self.judge_max_tokens = 8

    def initialize(self, config: Dict[str, Any]) -> None:
        """Select metrics and the optional judge; then the tool hook."""
        config = dict(config or {})
        self.metric_names = list(config.get("metrics", text_metrics.METRICS))
        unknown = [m for m in self.metric_names if m not in text_metrics.METRICS]
        if unknown:
            raise EvaluationError(f"unknown metrics {unknown}")
        self.judge = config.get("judge")
        self.judge_max_tokens = int(config.get("judge_max_tokens", 8))
        self._setup(config)
        self.initialized = True

    def evaluate(self, predictions: List[Any], references: List[Any], **kwargs) -> Dict[str, Any]:
        """Score predictions; ``questions=[...]`` improves the judge's context."""
        if not self.initialized:
            raise EvaluationError(f"{type(self).__name__} is not initialized")
        predictions = [str(p) for p in predictions]
        references = [str(r) for r in references]
        try:
            per_example = text_metrics.compute(predictions, references, self.metric_names)
        except ValueError as exc:
            raise EvaluationError(str(exc)) from exc
        summary = text_metrics.aggregate(per_example)

        if self.judge is not None:
            questions = kwargs.get("questions") or [""] * len(predictions)
            scores = [self._judge(q, p, r) for q, p, r in zip(questions, predictions, references)]
            valid = [s for s in scores if s is not None]
            per_example["judge_score"] = scores
            summary["judge_score"] = sum(valid) / len(valid) if valid else 0.0
            summary["judge_unparsed"] = float(len(scores) - len(valid))

        result = {"tool": self.TOOL, "n": len(predictions), "metrics": summary,
                  "per_example": per_example}
        result.update(self._log(result, kwargs))
        return result

    def shutdown(self) -> None:
        """Release the tool hook."""
        if self.initialized:
            self._teardown()
        self.initialized = False

    # -- hooks for tracking-tool subclasses -------------------------------

    def _setup(self, config: Dict[str, Any]) -> None:
        """Connect to the tracking tool (native: nothing)."""

    def _log(self, result: Dict[str, Any], kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Log ``result``; return extra keys for the result (e.g. run id)."""
        del result, kwargs
        return {}

    def _teardown(self) -> None:
        """Close the tracking tool (native: nothing)."""

    def _judge(self, question: str, prediction: str, reference: str) -> Optional[float]:
        prompt = JUDGE_PROMPT.format(question=question, reference=reference,
                                     prediction=prediction)
        reply = self.judge.chat_completion([{"role": "user", "content": prompt}],
                                           max_tokens=self.judge_max_tokens, temperature=0)
        return parse_judge_score(reply.text)
