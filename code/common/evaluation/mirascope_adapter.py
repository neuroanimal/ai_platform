"""Mirascope evaluation adapter - not implemented, on purpose.

Mirascope is a toolkit for *calling* LLMs (prompt functions, structured
outputs), not an evaluation library; an evaluation adapter would just be
an LLM judge, which the platform already has without the extra dependency.

Instead of returning constant metrics (what the earlier stub did), every
method raises ``NotImplementedError`` with this explanation. Equivalent
functionality that does work:

- ``NativeEvaluationAdapter`` with ``judge=<any platform LLM adapter>``.

The class name is kept so that registries and imports do not break.
"""

from typing import Any, Dict, List

from ai_platform.common.evaluation.base import EvaluationAdapter

_MESSAGE = (
    'MiraScopeAdapter is not implemented: Mirascope is an LLM-calling toolkit, not an evaluator.'
    ' Use NativeEvaluationAdapter with judge=<LLM adapter> instead.'
)


class MiraScopeAdapter(EvaluationAdapter):
    """Placeholder that refuses to pretend; see the module docstring."""

    def initialize(self, config: Dict[str, Any]) -> None:
        """Not implemented."""
        raise NotImplementedError(_MESSAGE)

    def evaluate(self, predictions: List[Any], references: List[Any], **kwargs) -> Dict[str, Any]:
        """Not implemented."""
        raise NotImplementedError(_MESSAGE)

    def shutdown(self) -> None:
        """Nothing to release."""
