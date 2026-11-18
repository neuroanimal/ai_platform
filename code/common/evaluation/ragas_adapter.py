"""RAGAS adapter (https://docs.ragas.io), ragas >= 0.2 API.

Builds an ``EvaluationDataset`` from single-turn samples and runs
``ragas.evaluate``. Most RAGAS metrics are LLM-judged, so an LLM (and for
some metrics embeddings) must be supplied in RAGAS's own wrapper types.

Configuration:

    metrics_objects   list of RAGAS metric instances (required), e.g.
                      [Faithfulness(), ResponseRelevancy()]
    llm, embeddings   RAGAS-wrapped models passed to ``ragas.evaluate``

``evaluate(predictions, references, questions=[...], contexts=[[...], ...])``
maps to the sample fields ``response``, ``reference``, ``user_input`` and
``retrieved_contexts``.

Result: ``{"tool": "RAGAS", "n", "metrics": {name: mean}, "per_example": {...}}``.
Not verified against an installed RAGAS here (the package was not installed
when this was written); RAGAS changed its API between 0.1 and 0.2, and this
adapter targets 0.2+. Previously a stub returning constant metrics; the
class name and the EvaluationAdapter methods are unchanged.
"""

import math
from typing import Any, Dict, List

from ai_platform.common.evaluation.base import EvaluationAdapter
from ai_platform.common.evaluation.native_evaluation_adapter import EvaluationError


class RAGASAdapter(EvaluationAdapter):
    """Runs RAGAS metrics."""

    TOOL = "RAGAS"

    def __init__(self):
        self.initialized = False
        self._ragas = None
        self._config: Dict[str, Any] = {}

    def initialize(self, config: Dict[str, Any]) -> None:
        """Import RAGAS and keep metrics and models."""
        try:
            import ragas  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise EvaluationError("RAGASAdapter requires: pip install ragas") from exc
        if not config.get("metrics_objects"):
            raise EvaluationError(
                "RAGASAdapter needs 'metrics_objects' (RAGAS metric instances)")
        self._ragas = ragas
        self._config = dict(config)
        self.initialized = True

    def evaluate(self, predictions: List[Any], references: List[Any], **kwargs) -> Dict[str, Any]:
        """Run ragas.evaluate and average the numeric score columns."""
        if not self.initialized:
            raise EvaluationError("RAGASAdapter is not initialized")
        n = len(predictions)
        if n != len(references):
            raise EvaluationError(f"{n} predictions but {len(references)} references")
        questions = kwargs.get("questions") or [""] * n
        contexts = kwargs.get("contexts") or [[] for _ in range(n)]
        samples = [{"user_input": q, "response": str(p), "reference": str(r),
                    "retrieved_contexts": list(c)}
                   for p, r, q, c in zip(predictions, references, questions, contexts)]
        dataset = self._ragas.EvaluationDataset.from_list(samples)
        options = {k: self._config[k] for k in ("llm", "embeddings") if self._config.get(k)}
        result = self._ragas.evaluate(dataset=dataset,
                                      metrics=self._config["metrics_objects"], **options)
        frame = result.to_pandas()
        per_example, means = {}, {}
        for column in frame.columns:
            values = frame[column].tolist()
            if values and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                              for v in values):
                per_example[column] = [float(v) for v in values]
                finite = [v for v in per_example[column] if not math.isnan(v)]
                means[column] = sum(finite) / len(finite) if finite else float("nan")
        return {"tool": self.TOOL, "n": n, "metrics": means, "per_example": per_example}

    def shutdown(self) -> None:
        """Release references."""
        self._ragas = None
        self.initialized = False
