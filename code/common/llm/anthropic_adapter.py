"""
Anthropic Claude adapter (Messages API, https://docs.anthropic.com/en/api/messages).

Reuses the configuration, key handling and HTTP transport of
OpenAICompatibleAdapter, but speaks the Messages protocol:

- ``system`` messages are moved to the top-level ``system`` field;
- ``max_tokens`` is mandatory in this API - DEFAULT_MAX_TOKENS applies when
  neither the configuration nor the call sets it;
- ``stop_reason`` is mapped to the OpenAI vocabulary ("max_tokens" -> "length",
  "end_turn"/"stop_sequence" -> "stop") so ChatResult.truncated works the
  same for every adapter.

Key from ``ANTHROPIC_API_KEY`` unless configured. ``model`` is required.
Previously a stub returning a fabricated string; the class name and the
LLMAdapter methods are unchanged.
"""

from typing import Any, Dict, List

from ai_platform.common.llm.chat_result import ChatResult
from ai_platform.common.llm.llm_exception import LLMResponseError
from ai_platform.common.llm.openai_compatible_adapter import OpenAICompatibleAdapter

_STOP_REASONS = {
    "end_turn": "stop",
    "stop_sequence": "stop",
    "max_tokens": "length",
    "tool_use": "tool_calls",
}


def split_system(messages: List[Dict[str, str]]):
    """Return (system_text, other_messages) for APIs with a separate system field."""
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    rest = [m for m in messages if m["role"] != "system"]
    return system, rest


class AnthropicAdapter(OpenAICompatibleAdapter):
    """Messages API adapter for Anthropic Claude models."""

    PROVIDER = "anthropic"
    DEFAULT_BASE_URL = "https://api.anthropic.com"
    DEFAULT_API_KEY_ENV = "ANTHROPIC_API_KEY"
    REQUIRES_API_KEY = True
    AUTH_HEADER = "x-api-key"
    AUTH_SCHEME = ""
    API_VERSION = "2023-06-01"
    DEFAULT_MAX_TOKENS = 1024

    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize and add the mandatory ``anthropic-version`` header."""
        config = dict(config or {})
        config["headers"] = {"anthropic-version": self.API_VERSION,
                             **(config.get("headers") or {})}
        super().initialize(config)

    def chat_completion(self, messages: List[Dict[str, str]],
                        allow_empty: bool = False, **kwargs) -> ChatResult:
        """Run one Messages API call and return text plus metadata."""
        client = self._require_client()
        self._validate_messages(messages)

        system, turns = split_system(messages)
        payload: Dict[str, Any] = {"model": kwargs.pop("model", self.model)}
        payload.update(self.default_params)
        payload.update(kwargs)
        payload.setdefault("max_tokens", self.DEFAULT_MAX_TOKENS)
        payload["messages"] = turns
        if system:
            payload["system"] = system

        response = self._call(client.post, self._path("/messages"), payload)
        data = response.data or {}

        try:
            text = "".join(
                block.get("text", "") for block in data["content"] if block.get("type") == "text"
            )
        except (KeyError, TypeError) as exc:
            raise LLMResponseError(
                f"anthropic: unexpected response shape: {str(data)[:300]}"
            ) from exc

        if not allow_empty and not text.strip():
            raise LLMResponseError(
                f"anthropic: model {payload['model']!r} returned an empty answer"
            )

        usage = data.get("usage") or {}
        prompt_tokens = usage.get("input_tokens", 0)
        completion_tokens = usage.get("output_tokens", 0)

        return ChatResult(
            text=text,
            model=data.get("model", payload["model"]),
            finish_reason=_STOP_REASONS.get(data.get("stop_reason"), data.get("stop_reason")),
            usage={"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
                   "total_tokens": prompt_tokens + completion_tokens},
            elapsed_seconds=response.elapsed_seconds,
            raw=data,
        )
