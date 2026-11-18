"""
Alibaba Cloud Model Studio (DashScope) OpenAI-compatible mode for Qwen models.

For the mainland-China region pass base_url="https://dashscope.aliyuncs.com/compatible-mode".
For a local Qwen (LocalAI, Ollama, vLLM) use those adapters instead.

Hosted endpoint: needs an API key, read from ``DASHSCOPE_API_KEY`` unless ``api_key`` or
``api_key_env`` is configured. ``model`` has no default on purpose - hosted
model names change faster than this code, so a stale default would fail
silently on the provider side instead of loudly here.

Previously a stub returning a fabricated string; the class name and the
LLMAdapter methods are unchanged.
"""

from ai_platform.common.llm.openai_compatible_adapter import OpenAICompatibleAdapter


class QwenAdapter(OpenAICompatibleAdapter):
    """Chat Completions adapter for the qwen hosted API."""

    PROVIDER = "qwen"
    DEFAULT_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode"
    DEFAULT_API_PREFIX = "/v1"
    DEFAULT_API_KEY_ENV = "DASHSCOPE_API_KEY"
    REQUIRES_API_KEY = True
