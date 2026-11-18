"""Hugging Face ``evaluate`` adapter.

Loads metrics with ``evaluate.load(name)`` and runs
``compute(predictions=..., references=...)`` for each. The library's
own implementations are used (e.g. "rouge", "bleu", "exact_match",
"bertscore"), so results match what Hugging Face reports.

Configuration:

    hf_metrics       list of metric names, default ["exact_match", "rouge"]
    compute_kwargs   {metric_name: {extra compute() kwargs}}, e.g.
                     {"bertscore": {"lang": "pl"}}

Result: ``{"tool": "HFEvaluate", "n": int, "metrics": {"<metric>.<key>": float, ...}}``
(non-numeric outputs are kept under ``raw``). Loading a metric may download
its script the first time. Not verified against an installed ``evaluate``
here (the package was not installed when this was written).
Previously a stub returning constant metrics; the class name and the
EvaluationAdapter methods are unchanged.
"""

from typing import Any, Dict, List

from ai_platform.common.evaluation.base import EvaluationAdapter
from ai_platform.common.evaluation.native_evaluation_adapter import EvaluationError


class HFEvaluateAdapter(EvaluationAdapter):
    """Metrics computed by the Hugging Face evaluate library."""

    TOOL = "HFEvaluate"

    def __init__(self):
        self.initialized = False
        self._loaded = {}
        self._compute_kwargs = {}

    def initialize(self, config: Dict[str, Any]) -> None:
        """Load the configured metrics."""
        try:
            import evaluate  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise EvaluationError("HFEvaluateAdapter requires: pip install evaluate") from exc
        names = config.get("hf_metrics", ["exact_match", "rouge"])
        self._loaded = {name: evaluate.load(name) for name in names}
        self._compute_kwargs = dict(config.get("compute_kwargs", {}))
        self.initialized = True

    def evaluate(self, predictions: List[Any], references: List[Any], **kwargs) -> Dict[str, Any]:
        """Run every loaded metric."""
        if not self.initialized:
            raise EvaluationError("HFEvaluateAdapter is not initialized")
        if len(predictions) != len(references):
            raise EvaluationError(
                f"{len(predictions)} predictions but {len(references)} references")
        metrics, raw = {}, {}
        for name, metric in self._loaded.items():
            output = metric.compute(predictions=list(predictions), references=list(references),
                                    **self._compute_kwargs.get(name, {}), **kwargs)
            for key, value in (output or {}).items():
                if isinstance(value, (int, float)):
                    metrics[f"{name}.{key}"] = float(value)
                else:
                    raw[f"{name}.{key}"] = value
        return {"tool": self.TOOL, "n": len(predictions), "metrics": metrics, "raw": raw}

    def shutdown(self) -> None:
        """Drop loaded metrics."""
        self._loaded = {}
        self.initialized = False
