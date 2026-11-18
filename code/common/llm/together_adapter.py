"""
Together AI API, OpenAI-compatible (https://docs.together.ai).

Hosted endpoint: needs an API key, read from ``TOGETHER_API_KEY`` unless ``api_key`` or
``api_key_env`` is configured. ``model`` has no default on purpose - hosted
model names change faster than this code, so a stale default would fail
silently on the provider side instead of loudly here.

Previously a stub returning a fabricated string; the class name and the
LLMAdapter methods are unchanged.
"""

from ai_platform.common.llm.openai_compatible_adapter import OpenAICompatibleAdapter


class TogetherAdapter(OpenAICompatibleAdapter):
    """Chat Completions adapter for the together hosted API."""

    PROVIDER = "together"
    DEFAULT_BASE_URL = "https://api.together.xyz"
    DEFAULT_API_PREFIX = "/v1"
    DEFAULT_API_KEY_ENV = "TOGETHER_API_KEY"
    REQUIRES_API_KEY = True
