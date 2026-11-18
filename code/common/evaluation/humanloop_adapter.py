"""Humanloop evaluation adapter - not implemented, on purpose.

Humanloop is a hosted platform; to the best of the author's knowledge the
service has been discontinued, so an adapter could not be built or
verified against it.

Instead of returning constant metrics (what the earlier stub did), every
method raises ``NotImplementedError`` with this explanation. Equivalent
functionality that does work:

- ``MLflowAdapter`` or ``LangSmithAdapter`` for tracking the same native
  metrics.

The class name is kept so that registries and imports do not break.
"""

from typing import Any, Dict, List

from ai_platform.common.evaluation.base import EvaluationAdapter

_MESSAGE = (
    'HumanLoopAdapter is not implemented: the Humanloop service is, '
    'to the best of our knowledge, discontinued.'
    ' Use MLflowAdapter or LangSmithAdapter instead.'
)


class HumanLoopAdapter(EvaluationAdapter):
    """Placeholder that refuses to pretend; see the module docstring."""

    def initialize(self, config: Dict[str, Any]) -> None:
        """Not implemented."""
        raise NotImplementedError(_MESSAGE)

    def evaluate(self, predictions: List[Any], references: List[Any], **kwargs) -> Dict[str, Any]:
        """Not implemented."""
        raise NotImplementedError(_MESSAGE)

    def shutdown(self) -> None:
        """Nothing to release."""
