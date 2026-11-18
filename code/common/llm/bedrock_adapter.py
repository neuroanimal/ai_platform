"""
AWS Bedrock adapter (Converse API via boto3).

Bedrock requests are signed with AWS SigV4, which is why this adapter uses
``boto3`` instead of the stdlib HTTP client. boto3 is imported lazily in
``initialize()``; when it is missing, ``LLMDependencyError`` names the
package to install.

Configuration:

    model        Bedrock model id or inference profile id (required)
    region       AWS region, default from the AWS configuration chain
    profile      named AWS profile (optional)
    temperature, max_tokens   defaults for every call
    client       a ready ``bedrock-runtime`` client (tests, custom sessions)

Credentials come from the standard AWS chain (env, profile, SSO, role);
this adapter never reads or stores keys itself.

``stopReason`` is mapped to the OpenAI vocabulary ("max_tokens" -> "length").
Previously a stub returning a fabricated string; the class name and the
LLMAdapter methods are unchanged.
"""

import time
from typing import Any, Dict, List, Optional

from ai_platform.common.llm.anthropic_adapter import _STOP_REASONS as ANTHROPIC_STOP_REASONS
from ai_platform.common.llm.anthropic_adapter import split_system
from ai_platform.common.llm.base import LLMAdapter
from ai_platform.common.llm.chat_result import ChatResult
from ai_platform.common.llm.llm_exception import (
    LLMConfigurationError,
    LLMDependencyError,
    LLMNotInitializedError,
    LLMRequestError,
    LLMResponseError,
)

# Bedrock's Converse API uses the same stop reasons as Anthropic's Messages API.
_STOP_REASONS = ANTHROPIC_STOP_REASONS


class BedrockAdapter(LLMAdapter):
    """Converse API adapter for models hosted on AWS Bedrock."""

    PROVIDER = "bedrock"

    def __init__(self) -> None:
        self.initialized = False
        self.model: Optional[str] = None
        self.default_params: Dict[str, Any] = {}
        self._client = None

    def initialize(self, config: Dict[str, Any]) -> None:
        """Create the bedrock-runtime client (no request is sent)."""
        config = dict(config or {})
        self.model = config.get("model")
        if not self.model:
            raise LLMConfigurationError("bedrock: 'model' is required")

        self.default_params = {k: config[k] for k in ("temperature", "max_tokens") if k in config}

        self._client = config.get("client")
        if self._client is None:
            try:
                import boto3  # pylint: disable=import-outside-toplevel
            except ImportError as exc:
                raise LLMDependencyError("BedrockAdapter", "boto3") from exc
            session = boto3.Session(profile_name=config.get("profile"))
            self._client = session.client("bedrock-runtime", region_name=config.get("region"))

        self.initialized = True

    def generate(self, prompt: str, **kwargs) -> str:
        """Single-turn completion of ``prompt``; returns the answer text."""
        return self.chat([{"role": "user", "content": prompt}], **kwargs)

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Multi-turn completion; returns the answer text."""
        return self.chat_completion(messages, **kwargs).text

    def chat_completion(self, messages: List[Dict[str, str]],
                        allow_empty: bool = False, **kwargs) -> ChatResult:
        """Run one Converse call and return text plus metadata."""
        if not self.initialized or self._client is None:
            raise LLMNotInitializedError(type(self).__name__)
        if not messages:
            raise LLMConfigurationError("messages must be a non-empty list")

        params = {**self.default_params, **kwargs}
        model = params.pop("model", self.model)
        inference = {}
        if "max_tokens" in params:
            inference["maxTokens"] = params.pop("max_tokens")
        if "temperature" in params:
            inference["temperature"] = params.pop("temperature")
        if "top_p" in params:
            inference["topP"] = params.pop("top_p")

        system, turns = split_system(messages)
        request: Dict[str, Any] = {
            "modelId": model,
            "messages": [{"role": m["role"], "content": [{"text": m["content"]}]} for m in turns],
        }
        if system:
            request["system"] = [{"text": system}]
        if inference:
            request["inferenceConfig"] = inference
        if params:
            request["additionalModelRequestFields"] = params

        start = time.perf_counter()
        try:
            data = self._client.converse(**request)
        except Exception as exc:  # botocore errors have no common importable base here
            raise LLMRequestError(f"bedrock: {exc}", 0) from exc
        elapsed = time.perf_counter() - start

        try:
            blocks = data["output"]["message"]["content"]
            text = "".join(block.get("text", "") for block in blocks)
        except (KeyError, TypeError) as exc:
            raise LLMResponseError(
                f"bedrock: unexpected response shape: {str(data)[:300]}"
            ) from exc

        if not allow_empty and not text.strip():
            raise LLMResponseError(f"bedrock: model {model!r} returned an empty answer")

        usage = data.get("usage") or {}
        return ChatResult(
            text=text,
            model=model,
            finish_reason=_STOP_REASONS.get(data.get("stopReason"), data.get("stopReason")),
            usage={"prompt_tokens": usage.get("inputTokens", 0),
                   "completion_tokens": usage.get("outputTokens", 0),
                   "total_tokens": usage.get("totalTokens", 0)},
            elapsed_seconds=elapsed,
            metrics={
                "server_latency_seconds":
                    (data.get("metrics") or {}).get("latencyMs", 0) / 1000,
            },
            raw=data,
        )

    def shutdown(self) -> None:
        """Drop the client."""
        self._client = None
        self.initialized = False
