"""
Adapter for any server that implements the OpenAI Chat Completions API.

This covers local runtimes (LocalAI, vLLM, llama.cpp server, Ollama's
``/v1`` endpoint, LM Studio) and hosted providers that expose the same
protocol (OpenAI, DeepSeek, xAI Grok, Mistral, Together AI, Azure OpenAI).
Provider adapters subclass it and only change the class-level defaults.

No third-party dependency: transport is ``HttpJsonClient`` (stdlib).

Configuration keys accepted by ``initialize()``:

    base_url      server root, e.g. "http://127.0.0.1:8080"   (or DEFAULT_BASE_URL)
    model         model id as the server knows it               (or DEFAULT_MODEL)
    api_key       secret; prefer api_key_env over inlining it
    api_key_env   name of the environment variable holding the key
    api_prefix    path prefix of the API, default "/v1"
    timeout       seconds per request, default 300
    temperature   default sampling temperature for every call
    max_tokens    default completion limit for every call
    headers       extra HTTP headers (dict)
    require_api_key  override REQUIRES_API_KEY, e.g. False for a local
                  server that speaks a hosted provider's protocol

Tools: pass ``tools=[...]`` (OpenAI function-tool schemas) to
``chat_completion``; requested calls come back in ``ChatResult.tool_calls``.

``stream_chat()`` streams the answer as ``StreamChunk`` objects (SSE).

Every keyword argument of ``chat()`` / ``chat_completion()`` that is not a
known option is forwarded verbatim into the request body, so server-specific
parameters (``top_p``, ``seed``, ``stop`` ...) need no adapter change.
"""

import json
import os
from typing import Any, Dict, Iterator, List, Optional

from ai_platform.common.llm.base import LLMAdapter
from ai_platform.common.llm.chat_result import ChatResult, StreamChunk, ToolCall
from ai_platform.common.llm.llm_exception import (
    LLMConfigurationError,
    LLMConnectionError,
    LLMNotInitializedError,
    LLMRequestError,
    LLMResponseError,
)
from ai_platform.common.util.http_json_client import (
    HttpConnectionError,
    HttpDecodeError,
    HttpJsonClient,
    HttpStatusError,
)


class OpenAICompatibleAdapter(LLMAdapter):
    """Chat Completions client for OpenAI-compatible servers."""

    #: Provider name used in messages and in the registry.
    PROVIDER = "openai-compatible"
    #: Used when ``base_url`` is not configured; ``None`` makes it required.
    DEFAULT_BASE_URL: Optional[str] = None
    #: Used when ``model`` is not configured; ``None`` makes it required.
    DEFAULT_MODEL: Optional[str] = None
    #: Environment variable consulted when neither api_key nor api_key_env is set.
    DEFAULT_API_KEY_ENV: Optional[str] = None
    #: Hosted providers refuse anonymous calls; local servers do not need a key.
    REQUIRES_API_KEY = False
    #: Header carrying the key and the prefix put before it.
    AUTH_HEADER = "Authorization"
    AUTH_SCHEME = "Bearer "
    DEFAULT_API_PREFIX = "/v1"
    DEFAULT_TIMEOUT = 300.0

    def __init__(self) -> None:
        self.initialized = False
        self.model: Optional[str] = None
        self.base_url: Optional[str] = None
        self.api_prefix = self.DEFAULT_API_PREFIX
        self.default_params: Dict[str, Any] = {}
        self._client: Optional[HttpJsonClient] = None

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------

    def initialize(self, config: Dict[str, Any]) -> None:
        """Validate the configuration and prepare the HTTP client.

        No request is sent here, so initialization works offline; use
        ``list_models()`` or ``health()`` to check the server.
        """
        config = dict(config or {})

        self.base_url = config.get("base_url") or self.DEFAULT_BASE_URL
        self.model = config.get("model") or self.DEFAULT_MODEL

        if not self.base_url:
            raise LLMConfigurationError(f"{self.PROVIDER}: 'base_url' is required")
        if not self.model:
            raise LLMConfigurationError(f"{self.PROVIDER}: 'model' is required")

        self.api_prefix = config.get("api_prefix", self.DEFAULT_API_PREFIX)
        self.default_params = {
            key: config[key] for key in ("temperature", "max_tokens") if key in config
        }

        headers = dict(config.get("headers") or {})
        api_key = self._resolve_api_key(config)

        if api_key:
            headers[self.AUTH_HEADER] = f"{self.AUTH_SCHEME}{api_key}"
        elif config.get("require_api_key", self.REQUIRES_API_KEY):
            env = config.get("api_key_env") or self.DEFAULT_API_KEY_ENV
            raise LLMConfigurationError(
                f"{self.PROVIDER}: API key missing - set 'api_key' or the "
                f"environment variable {env or '<api_key_env>'}"
            )

        self._client = HttpJsonClient(
            base_url=self.base_url,
            timeout=float(config.get("timeout", self.DEFAULT_TIMEOUT)),
            headers=headers,
        )
        self.initialized = True

    def shutdown(self) -> None:
        """Drop the client; the adapter must be initialized again before use."""
        self._client = None
        self.initialized = False

    # ------------------------------------------------------------------
    # LLMAdapter interface
    # ------------------------------------------------------------------

    def generate(self, prompt: str, **kwargs) -> str:
        """Single-turn completion of ``prompt``; returns the answer text."""
        return self.chat([{"role": "user", "content": prompt}], **kwargs)

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Multi-turn completion; returns the answer text."""
        return self.chat_completion(messages, **kwargs).text

    # ------------------------------------------------------------------
    # extended API
    # ------------------------------------------------------------------

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        allow_empty: bool = False,
        **kwargs,
    ) -> ChatResult:
        """Run one chat completion and return text plus metadata.

        ``allow_empty=False`` (default) raises ``LLMResponseError`` when the
        server returns an empty answer, which is what a caller usually wants
        to know about rather than silently receiving "".
        """
        client = self._require_client()
        payload = self._build_payload(messages, kwargs)

        response = self._call(client.post, self._path("/chat/completions"), payload)
        return self._parse_chat_response(response.data, payload["model"],
                                         response.elapsed_seconds, allow_empty)

    def stream_chat(self, messages: List[Dict[str, str]], **kwargs) -> Iterator[StreamChunk]:
        """Stream one chat completion (``stream: true``, Server-Sent Events).

        Yields ``StreamChunk`` objects as text arrives; the final chunk has the
        ``finish_reason`` (and ``usage`` if the server sends it - requested with
        ``stream_options.include_usage``, which some servers ignore).
        ``collect_stream`` turns the chunks back into a ``ChatResult``.
        """
        client = self._require_client()
        payload = self._build_payload(messages, kwargs)
        payload["stream"] = True
        payload.setdefault("stream_options", {"include_usage": True})
        try:
            for line in client.stream_lines("POST", self._path("/chat/completions"), payload):
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    return
                chunk = self._parse_stream_event(data)
                if chunk is not None:
                    yield chunk
        except HttpConnectionError as exc:
            raise LLMConnectionError(f"{self.PROVIDER}: {exc}") from exc
        except HttpStatusError as exc:
            raise LLMRequestError(f"{self.PROVIDER}: {exc}", exc.status) from exc

    def _parse_stream_event(self, data: str) -> Optional[StreamChunk]:
        try:
            event = json.loads(data)
        except json.JSONDecodeError as exc:
            raise LLMResponseError(f"{self.PROVIDER}: bad stream event {data[:200]!r}") from exc
        choices = event.get("choices") or []
        usage = event.get("usage") or {}
        if not choices:
            return StreamChunk("", None, usage) if usage else None
        choice = choices[0]
        delta = choice.get("delta") or {}
        return StreamChunk(delta.get("content") or "", choice.get("finish_reason"), usage)

    def list_models(self) -> List[str]:
        """Return model ids served by the endpoint (``GET /v1/models``)."""
        client = self._require_client()
        response = self._call(client.get, self._path("/models"))
        data = response.data if isinstance(response.data, dict) else {}
        return [item.get("id") for item in data.get("data", []) if item.get("id")]

    def health(self) -> Dict[str, Any]:
        """Report whether the server answers and serves the configured model."""
        try:
            models = self.list_models()
        except (LLMConnectionError, LLMRequestError, LLMResponseError) as exc:
            return {"reachable": False, "model_available": False, "error": str(exc)}
        return {
            "reachable": True,
            "model_available": self.model in models,
            "models": models,
        }

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _build_payload(self, messages: List[Dict[str, str]],
                       kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate messages and merge model, defaults and call options.

        Precedence: per-call keyword arguments > configured defaults.
        """
        self._validate_messages(messages)
        payload: Dict[str, Any] = {"model": kwargs.pop("model", self.model)}
        payload.update(self.default_params)
        payload.update(kwargs)
        payload["messages"] = messages
        payload.setdefault("stream", False)
        return payload

    def _resolve_api_key(self, config: Dict[str, Any]) -> Optional[str]:
        if config.get("api_key"):
            return config["api_key"]
        env = config.get("api_key_env") or self.DEFAULT_API_KEY_ENV
        return os.environ.get(env) if env else None

    def _require_client(self) -> HttpJsonClient:
        if not self.initialized or self._client is None:
            raise LLMNotInitializedError(type(self).__name__)
        return self._client

    def _path(self, endpoint: str) -> str:
        return self.api_prefix.rstrip("/") + endpoint

    def _call(self, method, *args):
        """Invoke a client method and translate transport errors."""
        try:
            return method(*args)
        except HttpConnectionError as exc:
            raise LLMConnectionError(f"{self.PROVIDER}: {exc}") from exc
        except HttpStatusError as exc:
            raise LLMRequestError(f"{self.PROVIDER}: {exc}", exc.status) from exc
        except HttpDecodeError as exc:
            raise LLMResponseError(f"{self.PROVIDER}: {exc}") from exc

    @staticmethod
    def _validate_messages(messages: List[Dict[str, str]]) -> None:
        if not isinstance(messages, list) or not messages:
            raise LLMConfigurationError("messages must be a non-empty list")
        for message in messages:
            # Assistant messages that only call tools may carry content None.
            if isinstance(message, dict) and message.get("tool_calls"):
                continue
            if not isinstance(message, dict) or "role" not in message or "content" not in message:
                raise LLMConfigurationError(
                    f"each message needs 'role' and 'content', got: {message!r}"
                )

    def _parse_chat_response(self, data: Any, model: str, elapsed: float,
                             allow_empty: bool) -> ChatResult:
        try:
            choice = data["choices"][0]
            text = choice["message"].get("content") or ""
            tool_calls = parse_tool_calls(choice["message"].get("tool_calls") or [])
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise LLMResponseError(
                f"{self.PROVIDER}: unexpected response shape: {str(data)[:300]}"
            ) from exc

        # An answer that only calls tools is not empty.
        if not allow_empty and not text.strip() and not tool_calls:
            raise LLMResponseError(f"{self.PROVIDER}: model {model!r} returned an empty answer")

        return ChatResult(
            text=text,
            model=data.get("model") or model,
            finish_reason=choice.get("finish_reason"),
            usage=data.get("usage") or {},
            elapsed_seconds=elapsed,
            raw=data,
            tool_calls=tool_calls,
        )


def collect_stream(chunks: Iterator[StreamChunk], model: str = "",
                   elapsed_seconds: float = 0.0) -> ChatResult:
    """Join streamed chunks into one ChatResult."""
    text, finish_reason, usage = [], None, {}
    for chunk in chunks:
        text.append(chunk.text)
        finish_reason = chunk.finish_reason or finish_reason
        usage = chunk.usage or usage
    return ChatResult(text="".join(text), model=model, finish_reason=finish_reason,
                      usage=usage, elapsed_seconds=elapsed_seconds)


def parse_tool_calls(entries: List[Dict[str, Any]]) -> List[ToolCall]:
    """OpenAI ``message.tool_calls`` -> ToolCall objects (bad JSON arguments kept, flagged)."""
    calls = []
    for number, entry in enumerate(entries):
        function = entry.get("function") or {}
        raw = function.get("arguments")
        if isinstance(raw, dict):  # some servers send an object instead of a JSON string
            raw_text, arguments, error = json.dumps(raw), raw, None
        else:
            raw_text, arguments, error = str(raw or ""), {}, None
            try:
                decoded = json.loads(raw_text) if raw_text.strip() else {}
                if isinstance(decoded, dict):
                    arguments = decoded
                else:
                    error = "arguments are not a JSON object"
            except json.JSONDecodeError as exc:
                error = f"arguments are not valid JSON: {exc}"
        calls.append(ToolCall(call_id=str(entry.get("id") or f"call_{number}"),
                              name=str(function.get("name") or ""), arguments=arguments,
                              raw_arguments=raw_text, arguments_error=error))
    return calls
