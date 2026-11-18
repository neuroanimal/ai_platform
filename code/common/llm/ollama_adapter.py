"""
Ollama adapter (https://ollama.com).

Two ways of talking to Ollama, both real:

- ``chat()`` / ``chat_completion()`` use Ollama's OpenAI-compatible ``/v1``
  endpoint, so results look exactly like those of every other
  OpenAI-compatible adapter;
- ``native_chat_completion()`` uses the native ``/api/chat`` endpoint, which
  additionally reports server-side timings (model load, prompt evaluation,
  generation) - the figures benchmarks need to separate load time from
  inference time.

Earlier this module was a stub returning a fabricated string; the public
names (``OllamaAdapter``, ``initialize``, ``generate``, ``chat``,
``shutdown``) are kept so existing callers keep working.
"""

from typing import Any, Dict, List

from ai_platform.common.llm.chat_result import ChatResult
from ai_platform.common.llm.llm_exception import LLMResponseError
from ai_platform.common.llm.openai_compatible_adapter import OpenAICompatibleAdapter

# Native Ollama reports durations in nanoseconds.
_NS = 1e9

# OpenAI-style option names mapped to Ollama's native "options" keys.
_NATIVE_OPTION_NAMES = {
    "max_tokens": "num_predict",
    "temperature": "temperature",
    "top_p": "top_p",
    "seed": "seed",
    "stop": "stop",
}


class OllamaAdapter(OpenAICompatibleAdapter):
    """Adapter for a local Ollama server."""

    PROVIDER = "ollama"
    DEFAULT_BASE_URL = "http://127.0.0.1:11434"
    DEFAULT_MODEL = "llama2"
    REQUIRES_API_KEY = False

    def version(self) -> str:
        """Return the Ollama server version (``GET /api/version``)."""
        client = self._require_client()
        response = self._call(client.get, "/api/version")
        return (response.data or {}).get("version", "unknown")

    def list_local_models(self) -> List[Dict[str, Any]]:
        """Return installed models with size and details (``GET /api/tags``)."""
        client = self._require_client()
        response = self._call(client.get, "/api/tags")
        return list((response.data or {}).get("models", []))

    def native_chat_completion(
        self,
        messages: List[Dict[str, str]],
        keep_alive: str = "5m",
        allow_empty: bool = False,
        **kwargs,
    ) -> ChatResult:
        """Chat through ``/api/chat`` and return server-side timings in ``metrics``.

        OpenAI-style keyword arguments (``max_tokens``, ``temperature``,
        ``top_p``, ``seed``, ``stop``) are mapped to Ollama options; any
        other keyword is passed into ``options`` unchanged (e.g. ``num_ctx``).
        """
        client = self._require_client()
        self._validate_messages(messages)

        params = {**self.default_params, **kwargs}
        model = params.pop("model", self.model)
        options = {
            _NATIVE_OPTION_NAMES.get(key, key): value for key, value in params.items()
        }

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "keep_alive": keep_alive,
            "options": options,
        }

        response = self._call(client.post, "/api/chat", payload)
        data = response.data or {}
        text = (data.get("message") or {}).get("content") or ""

        if not allow_empty and not text.strip():
            raise LLMResponseError(f"ollama: model {model!r} returned an empty answer")

        prompt_tokens = data.get("prompt_eval_count", 0)
        completion_tokens = data.get("eval_count", 0)
        eval_seconds = data.get("eval_duration", 0) / _NS

        metrics = {
            "total_seconds": data.get("total_duration", 0) / _NS,
            "load_seconds": data.get("load_duration", 0) / _NS,
            "prompt_eval_seconds": data.get("prompt_eval_duration", 0) / _NS,
            "eval_seconds": eval_seconds,
            "tokens_per_second": completion_tokens / eval_seconds if eval_seconds else 0.0,
        }

        return ChatResult(
            text=text,
            model=data.get("model", model),
            # Ollama says "length" / "stop" in done_reason, same vocabulary as OpenAI.
            finish_reason=data.get("done_reason"),
            usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            elapsed_seconds=response.elapsed_seconds,
            metrics=metrics,
            raw=data,
        )
