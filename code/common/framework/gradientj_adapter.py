"""GradientJ adapter - not implemented, on purpose.

GradientJ was a hosted LLM-app platform; no current public API could be
found or verified, so an adapter would be guesswork.

Instead of echoing the task (what the earlier stub did), every method
raises ``NotImplementedError``. Working alternatives: ``LangChainAdapter`` with a
platform LLM adapter.

The class name is kept so that registries and imports do not break.
"""

from typing import Any, Dict

from ai_platform.common.framework.base import FrameworkAdapter

_MESSAGE = (
    "GradientJAdapter is not implemented: no current public GradientJ API could be verified. "
    "Use LangChainAdapter instead."
)


class GradientJAdapter(FrameworkAdapter):
    """Placeholder that refuses to pretend; see the module docstring."""

    def initialize(self, config: Dict[str, Any]) -> None:
        """Not implemented."""
        raise NotImplementedError(_MESSAGE)

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Not implemented."""
        raise NotImplementedError(_MESSAGE)

    def shutdown(self) -> None:
        """Nothing to release."""
