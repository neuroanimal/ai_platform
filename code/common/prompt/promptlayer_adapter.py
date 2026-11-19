"""PromptLayer adapter: render templates stored in the PromptLayer registry.

Uses the ``promptlayer`` SDK (imported lazily):
``PromptLayer(api_key).templates.get(name, {"input_variables": variables})``
returns the template with the variables filled in by PromptLayer. Chat
templates are returned as "role: text" lines, completion templates as text.

Configuration:

    api_key / api_key_env   default env PROMPTLAYER_API_KEY
    client                  a ready PromptLayer client (tests)
    version / label         optional template version or release label

Not verified against the PromptLayer service here (no API key); unit tests
use a fake client. Previously a stub with a hard-coded "mock_key"; the
class name and the PromptAdapter methods are unchanged.
"""

import os
from typing import Any, Dict

from ai_platform.common.prompt.base import PromptAdapter
from ai_platform.common.prompt.jinja2_prompt_adapter import PromptError


def _text_of(content) -> str:
    """PromptLayer content is a list of {"type": "text", "text": ...} blocks."""
    if isinstance(content, str):
        return content
    return "".join(block.get("text", "") for block in content or [] if block.get("type") == "text")


class PromptLayerAdapter(PromptAdapter):
    """Templates rendered by the PromptLayer registry."""

    def __init__(self):
        self.initialized = False
        self.api_key = None
        self._client = None
        self._selector: Dict[str, Any] = {}

    def initialize(self, config: Dict[str, Any]) -> None:
        """Create the SDK client."""
        config = dict(config or {})
        self._client = config.get("client")
        self._selector = {k: config[k] for k in ("version", "label") if config.get(k)}
        if self._client is None:
            self.api_key = config.get("api_key") or os.environ.get(
                config.get("api_key_env") or "PROMPTLAYER_API_KEY")
            if not self.api_key:
                raise PromptError("promptlayer: API key missing (PROMPTLAYER_API_KEY)")
            try:
                from promptlayer import PromptLayer  # pylint: disable=import-outside-toplevel
            except ImportError as exc:
                raise PromptError("PromptLayerAdapter requires: pip install promptlayer") from exc
            self._client = PromptLayer(api_key=self.api_key)
        self.initialized = True

    def render(self, template: str, variables: Dict[str, Any]) -> str:
        """Fetch template ``template`` filled with ``variables``."""
        if not self.initialized:
            raise PromptError("PromptLayerAdapter is not initialized")
        answer = self._client.templates.get(
            template, {"input_variables": dict(variables or {}), **self._selector})
        if not answer:
            raise PromptError(f"promptlayer: template {template!r} not found")
        body = answer.get("prompt_template") or {}
        if body.get("type") == "chat":
            return "\n".join(f"{m.get('role')}: {_text_of(m.get('content'))}"
                             for m in body.get("messages", []))
        return _text_of(body.get("content"))

    def shutdown(self) -> None:
        """Drop the client."""
        self._client = None
        self.initialized = False
