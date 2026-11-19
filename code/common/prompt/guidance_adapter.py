"""Guidance prompt adapter - not implemented, on purpose.

Current Guidance releases are programs executed against a model (interleaved
generation and constraints), not templates rendered to text; rendering
without a model, which is what PromptAdapter.render means, does not exist
there. A Guidance integration belongs next to the LLM adapters, as an
execution strategy, not here.

Instead of returning a fabricated string (what the earlier stub did), every
method raises ``NotImplementedError`` with this explanation. Alternatives
that work: ``Jinja2PromptAdapter`` (sandboxed templates),
``LangChainPromptAdapter``, ``PriomptAdapter`` (token-budgeted assembly).

The class name is kept so that registries and imports do not break.
"""

from typing import Any, Dict

from ai_platform.common.prompt.base import PromptAdapter

_MESSAGE = (
    "GuidanceAdapter is not implemented: Guidance programs run against a model; "
    "there is no model-free render. "
    "Use Jinja2PromptAdapter or LangChainPromptAdapter instead."
)


class GuidanceAdapter(PromptAdapter):
    """Placeholder that refuses to pretend; see the module docstring."""

    def initialize(self, config: Dict[str, Any]) -> None:
        """Not implemented."""
        raise NotImplementedError(_MESSAGE)

    def render(self, template: str, variables: Dict[str, Any]) -> str:
        """Not implemented."""
        raise NotImplementedError(_MESSAGE)

    def shutdown(self) -> None:
        """Nothing to release."""
