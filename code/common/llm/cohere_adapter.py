"""
Cohere adapter (Chat API v2, https://docs.cohere.com/reference/chat).

Reuses configuration, Bearer key handling and transport of
OpenAICompatibleAdapter; v2 accepts OpenAI-style ``messages`` (including
``system``), so only the endpoint and the response shape differ:

- answer text is the concatenation of ``message.content[*].text``;
- ``finish_reason`` is mapped to the OpenAI vocabulary
  ("COMPLETE"/"STOP_SEQUENCE" -> "stop", "MAX_TOKENS" -> "length").

Key from ``CO_API_KEY`` unless configured. ``model`` is required.
Previously a stub returning a fabricated string; the class name and the
LLMAdapter methods are unchanged.
"""

from typing import Dict, List

from ai_platform.common.llm.chat_result import ChatResult
from ai_platform.common.llm.llm_exception import LLMResponseError
from ai_platform.common.llm.openai_compatible_adapter import OpenAICompatibleAdapter

_FINISH_REASONS = {
    "COMPLETE": "stop",
    "STOP_SEQUENCE": "stop",
    "MAX_TOKENS": "length",
    "TOOL_CALL": "tool_calls",
    "ERROR": "error",
}


class CohereAdapter(OpenAICompatibleAdapter):
    """Chat v2 adapter for Cohere models."""

    PROVIDER = "cohere"
    DEFAULT_BASE_URL = "https://api.cohere.com"
    DEFAULT_API_PREFIX = "/v2"
    DEFAULT_API_KEY_ENV = "CO_API_KEY"
    REQUIRES_API_KEY = True

    def chat_completion(self, messages: List[Dict[str, str]],
                        allow_empty: bool = False, **kwargs) -> ChatResult:
        """Run one Chat v2 call and return text plus metadata."""
        client = self._require_client()
        payload = self._build_payload(messages, kwargs)

        response = self._call(client.post, self._path("/chat"), payload)
        data = response.data or {}

        try:
            content = data["message"]["content"] or []
            text = "".join(part.get("text", "") for part in content if part.get("type") == "text")
        except (KeyError, TypeError) as exc:
            raise LLMResponseError(f"cohere: unexpected response shape: {str(data)[:300]}") from exc

        if not allow_empty and not text.strip():
            raise LLMResponseError(f"cohere: model {payload['model']!r} returned an empty answer")

        tokens = (data.get("usage") or {}).get("tokens") or {}
        prompt_tokens = int(tokens.get("input_tokens", 0))
        completion_tokens = int(tokens.get("output_tokens", 0))

        return ChatResult(
            text=text,
            model=payload["model"],
            finish_reason=_FINISH_REASONS.get(data.get("finish_reason"), data.get("finish_reason")),
            usage={"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
                   "total_tokens": prompt_tokens + completion_tokens},
            elapsed_seconds=response.elapsed_seconds,
            raw=data,
        )
