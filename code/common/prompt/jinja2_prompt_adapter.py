"""Jinja2 prompt adapter (new; add-only).

Renders prompt templates with Jinja2 in a *sandboxed* environment, so a
template taken from configuration or user input cannot reach Python
internals (attribute access to dunder members, calling arbitrary
callables). Undefined variables raise instead of rendering as empty text,
because a silently empty slot in a prompt is a bug that is hard to see.

Configuration:

    templates   {name: template_source}; render(name, variables) uses a
                named template, otherwise ``template`` itself is the source
    strict      raise on undefined variables (default True)
    trim_blocks / lstrip_blocks   Jinja2 whitespace control (default True)
"""

from typing import Any, Dict

from ai_platform.common.prompt.base import PromptAdapter


class PromptError(Exception):
    """Prompt rendering misuse or failure."""


class Jinja2PromptAdapter(PromptAdapter):
    """Sandboxed Jinja2 rendering."""

    def __init__(self):
        self.initialized = False
        self.templates: Dict[str, str] = {}
        self._env = None

    def initialize(self, config: Dict[str, Any]) -> None:
        """Create the sandboxed environment."""
        try:
            from jinja2 import StrictUndefined, Undefined  # pylint: disable=import-outside-toplevel
            from jinja2.sandbox import SandboxedEnvironment  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise PromptError("Jinja2PromptAdapter requires: pip install jinja2") from exc
        config = dict(config or {})
        self.templates = dict(config.get("templates", {}))
        self._env = SandboxedEnvironment(
            undefined=StrictUndefined if config.get("strict", True) else Undefined,
            trim_blocks=config.get("trim_blocks", True),
            lstrip_blocks=config.get("lstrip_blocks", True),
            autoescape=False,  # prompts are plain text, not HTML
        )
        self.initialized = True

    def render(self, template: str, variables: Dict[str, Any]) -> str:
        """Render a named template or a template source."""
        if not self.initialized:
            raise PromptError("Jinja2PromptAdapter is not initialized")
        from jinja2 import TemplateError  # pylint: disable=import-outside-toplevel
        source = self.templates.get(template, template)
        try:
            return self._env.from_string(source).render(**(variables or {}))
        except TemplateError as exc:
            raise PromptError(f"jinja2: {exc}") from exc

    def shutdown(self) -> None:
        """Drop the environment."""
        self._env = None
        self.initialized = False
