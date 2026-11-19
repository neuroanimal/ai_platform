"""LangChain prompt adapter (``langchain-core`` PromptTemplate).

Configuration:

    templates         {name: template_source}; render(name, ...) uses a
                      named template, otherwise ``template`` is the source
    template_format   "f-string" (default), "jinja2" or "mustache"

Missing variables raise ``PromptError`` (LangChain's KeyError, translated).
Note: LangChain's own docs advise against "jinja2" templates from untrusted
sources; use ``Jinja2PromptAdapter`` (sandboxed) for those.

Previously a stub returning a fabricated string; the class name and the
PromptAdapter methods are unchanged.
"""

from typing import Any, Dict

from ai_platform.common.prompt.base import PromptAdapter
from ai_platform.common.prompt.jinja2_prompt_adapter import PromptError


class LangChainPromptAdapter(PromptAdapter):
    """Renders with langchain_core.prompts.PromptTemplate."""

    def __init__(self):
        self.initialized = False
        self.prompt_templates: Dict[str, str] = {}
        self.template_format = "f-string"
        self._template_cls = None

    def initialize(self, config: Dict[str, Any]) -> None:
        """Import LangChain and keep the named templates."""
        try:
            from langchain_core.prompts import PromptTemplate  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise PromptError(
                "LangChainPromptAdapter requires: pip install langchain-core") from exc
        config = dict(config or {})
        self._template_cls = PromptTemplate
        self.prompt_templates = dict(config.get("templates", {}))
        self.template_format = config.get("template_format", "f-string")
        self.initialized = True

    def render(self, template: str, variables: Dict[str, Any]) -> str:
        """Format a named template or a template source."""
        if not self.initialized:
            raise PromptError("LangChainPromptAdapter is not initialized")
        source = self.prompt_templates.get(template, template)
        prompt = self._template_cls.from_template(source, template_format=self.template_format)
        missing = sorted(set(prompt.input_variables) - set(variables or {}))
        if missing:
            raise PromptError(f"langchain: missing variables {missing}")
        return prompt.format(**(variables or {}))

    def shutdown(self) -> None:
        """Forget templates."""
        self.prompt_templates = {}
        self.initialized = False
