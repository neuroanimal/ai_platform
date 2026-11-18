"""TruLens evaluation adapter - not implemented, on purpose.

TruLens evaluates *running applications*: it instruments an app, records
traces and applies feedback functions to them. That does not map onto
``evaluate(predictions, references)`` without inventing an app around the
data, and its API has changed substantially between releases
(``trulens_eval`` -> ``trulens``).

Instead of returning constant metrics (what the earlier stub did), every
method raises ``NotImplementedError`` with this explanation. Equivalent
functionality that does work:

- ``NativeEvaluationAdapter`` with ``judge=<LLM adapter>`` for LLM-judged scores;
- ``RAGASAdapter`` / ``DeepEvalAdapter`` for RAG-specific judged metrics.

The class name is kept so that registries and imports do not break.
"""

from typing import Any, Dict, List

from ai_platform.common.evaluation.base import EvaluationAdapter

_MESSAGE = (
    'TrulensAdapter is not implemented: TruLens evaluates instrumented apps, '
    'not prediction/reference lists.'
    ' Use NativeEvaluationAdapter (judge=...) or RAGASAdapter instead.'
)


class TrulensAdapter(EvaluationAdapter):
    """Placeholder that refuses to pretend; see the module docstring."""

    def initialize(self, config: Dict[str, Any]) -> None:
        """Not implemented."""
        raise NotImplementedError(_MESSAGE)

    def evaluate(self, predictions: List[Any], references: List[Any], **kwargs) -> Dict[str, Any]:
        """Not implemented."""
        raise NotImplementedError(_MESSAGE)

    def shutdown(self) -> None:
        """Nothing to release."""
