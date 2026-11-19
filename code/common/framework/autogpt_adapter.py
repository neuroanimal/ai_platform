"""AutoGPT adapter - not implemented, on purpose.

AutoGPT today is a platform (server, web builder, marketplace of agents),
not a library with a stable programmatic interface for running a goal from
Python; the classic goal-loop CLI it started as is no longer the product.

Instead of echoing the task (what the earlier stub did), every method
raises ``NotImplementedError``. Working alternatives: ``LangGraphAdapter``,
``AutoGenAdapter``, ``CrewAIAdapter``.

The class name is kept so that registries and imports do not break.
"""

from typing import Any, Dict

from ai_platform.common.framework.base import FrameworkAdapter

_MESSAGE = (
    "AutoGPTAdapter is not implemented: AutoGPT is a platform without a stable Python run API. "
    "Use LangGraphAdapter, AutoGenAdapter or CrewAIAdapter instead."
)


class AutoGPTAdapter(FrameworkAdapter):
    """Placeholder that refuses to pretend; see the module docstring."""

    def initialize(self, config: Dict[str, Any]) -> None:
        """Not implemented."""
        raise NotImplementedError(_MESSAGE)

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Not implemented."""
        raise NotImplementedError(_MESSAGE)

    def shutdown(self) -> None:
        """Nothing to release."""
