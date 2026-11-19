"""
Replicate adapter (predictions API, https://replicate.com/docs/reference/http).

Replicate runs arbitrary models, so there is no chat protocol: messages are
flattened into a single ``prompt`` input (``system`` goes to
``system_prompt``, which most Replicate LLMs accept). Other keyword arguments
are passed into ``input`` unchanged, ``max_tokens`` included.

Flow: POST /v1/models/<owner>/<name>/predictions with ``Prefer: wait``; if
the prediction has not finished within the wait window, poll ``urls.get``
every POLL_INTERVAL seconds until ``succeeded``/``failed``/``canceled`` or
the adapter ``timeout`` is reached.

Key from ``REPLICATE_API_TOKEN`` unless configured. ``model`` ("owner/name")
is required. Replicate does not report a finish reason, so
``ChatResult.finish_reason`` is None.

Previously a stub returning a fabricated string; the class name and the
LLMAdapter methods are unchanged.
"""

import time
from typing import Any, Dict, List

from ai_platform.common.llm.anthropic_adapter import split_system
from ai_platform.common.llm.chat_result import ChatResult
from ai_platform.common.llm.llm_exception import LLMError, LLMRequestError, LLMResponseError
from ai_platform.common.llm.openai_compatible_adapter import OpenAICompatibleAdapter

_TERMINAL = {"succeeded", "failed", "canceled"}


def flatten_messages(messages: List[Dict[str, str]]) -> str:
    """Render user/assistant turns as a plain-text transcript."""
    if len(messages) == 1:
        return messages[0]["content"]
    return "\n".join(f"{m['role']}: {m['content']}" for m in messages) + "\nassistant:"


class ReplicateAdapter(OpenAICompatibleAdapter):
    """Predictions adapter for language models hosted on Replicate."""

    PROVIDER = "replicate"
    DEFAULT_BASE_URL = "https://api.replicate.com"
    DEFAULT_API_KEY_ENV = "REPLICATE_API_TOKEN"
    REQUIRES_API_KEY = True
    POLL_INTERVAL = 1.0

    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize and ask the server to hold the response until done."""
        config = dict(config or {})
        config["headers"] = {"Prefer": "wait", **(config.get("headers") or {})}
        super().initialize(config)

    def chat_completion(self, messages: List[Dict[str, str]],
                        allow_empty: bool = False, **kwargs) -> ChatResult:
        """Create a prediction, wait for it, and return its output text."""
        client = self._require_client()
        self._validate_messages(messages)

        model = kwargs.pop("model", self.model)
        system, turns = split_system(messages)
        inputs: Dict[str, Any] = {**self.default_params, **kwargs,
                                  "prompt": flatten_messages(turns)}
        if system:
            inputs["system_prompt"] = system

        start = time.perf_counter()
        response = self._call(client.post, self._path(f"/models/{model}/predictions"),
                              {"input": inputs})
        prediction = self._wait(response.data or {}, start)
        elapsed = time.perf_counter() - start

        if prediction.get("status") != "succeeded":
            raise LLMRequestError(
                f"replicate: prediction {prediction.get('id')} ended with status "
                f"{prediction.get('status')}: {prediction.get('error')}", 0)

        output = prediction.get("output")
        text = "".join(output) if isinstance(output, list) else str(output or "")

        if not allow_empty and not text.strip():
            raise LLMResponseError(f"replicate: model {model!r} returned an empty answer")

        metrics = {k: float(v) for k, v in (prediction.get("metrics") or {}).items()
                   if isinstance(v, (int, float))}
        return ChatResult(
            text=text,
            model=model,
            finish_reason=None,
            usage={"prompt_tokens": metrics.get("input_token_count", 0),
                   "completion_tokens": metrics.get("output_token_count", 0)},
            elapsed_seconds=elapsed,
            metrics=metrics,
            raw=prediction,
        )

    def list_models(self) -> List[str]:
        """Replicate has no per-account model list relevant to chat; not supported."""
        raise NotImplementedError("replicate: list_models is not supported - pass 'owner/name'")

    def health(self) -> Dict[str, Any]:
        """Check that the API answers and the configured model exists."""
        client = self._require_client()
        try:
            self._call(client.get, self._path(f"/models/{self.model}"))
        except (LLMRequestError, LLMResponseError) as exc:
            return {"reachable": True, "model_available": False, "error": str(exc)}
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return {"reachable": False, "model_available": False, "error": str(exc)}
        return {"reachable": True, "model_available": True}

    def _wait(self, prediction: Dict[str, Any], start: float) -> Dict[str, Any]:
        """Poll a prediction until it reaches a terminal status or times out."""
        client = self._require_client()
        while prediction.get("status") not in _TERMINAL:
            if time.perf_counter() - start > client.timeout:
                raise LLMRequestError(
                    f"replicate: prediction {prediction.get('id')} not finished "
                    f"after {client.timeout:.0f} s", 0)
            time.sleep(self.POLL_INTERVAL)
            url = (prediction.get("urls") or {}).get("get")
            if not url or not url.startswith(client.base_url.rstrip("/")):
                raise LLMResponseError(
                    f"replicate: no usable polling URL in {str(prediction)[:200]}"
                )
            prediction = self._call(client.get, url[len(client.base_url.rstrip("/")):]).data or {}
        return prediction

    def stream_chat(self, messages, **kwargs):
        """Not available yet: this provider streams with its own event format."""
        raise LLMError("ReplicateAdapter: streaming is not implemented yet; use chat_completion()")
