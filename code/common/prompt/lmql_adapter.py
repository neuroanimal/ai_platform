"""LMQL prompt adapter - not implemented, on purpose.

LMQL is a query language whose queries are *executed* against a model with
constraints; there is no model-free rendering step. To the best of the
author's knowledge the project is also no longer actively developed.

Instead of returning a fabricated string (what the earlier stub did), every
method raises ``NotImplementedError`` with this explanation. Alternatives
that work: ``Jinja2PromptAdapter`` (sandboxed templates),
``LangChainPromptAdapter``, ``PriomptAdapter`` (token-budgeted assembly).

The class name is kept so that registries and imports do not break.
"""

from typing import Any, Dict

from ai_platform.common.prompt.base import PromptAdapter

_MESSAGE = (
    "LMQLAdapter is not implemented: LMQL queries run against a model; "
    "there is no model-free render. "
    "Use Jinja2PromptAdapter or LangChainPromptAdapter instead."
)


class LMQLAdapter(PromptAdapter):
    """Placeholder that refuses to pretend; see the module docstring."""

    def initialize(self, config: Dict[str, Any]) -> None:
        """Not implemented."""
        raise NotImplementedError(_MESSAGE)

    def render(self, template: str, variables: Dict[str, Any]) -> str:
        """Not implemented."""
        raise NotImplementedError(_MESSAGE)

    def shutdown(self) -> None:
        """Nothing to release."""
