"""
xAI Grok API, OpenAI-compatible (https://docs.x.ai).

Hosted endpoint: needs an API key, read from ``XAI_API_KEY`` unless ``api_key`` or
``api_key_env`` is configured. ``model`` has no default on purpose - hosted
model names change faster than this code, so a stale default would fail
silently on the provider side instead of loudly here.

Previously a stub returning a fabricated string; the class name and the
LLMAdapter methods are unchanged.
"""

from ai_platform.common.llm.openai_compatible_adapter import OpenAICompatibleAdapter


class GrokAdapter(OpenAICompatibleAdapter):
    """Chat Completions adapter for the grok hosted API."""

    PROVIDER = "grok"
    DEFAULT_BASE_URL = "https://api.x.ai"
    DEFAULT_API_PREFIX = "/v1"
    DEFAULT_API_KEY_ENV = "XAI_API_KEY"
    REQUIRES_API_KEY = True
