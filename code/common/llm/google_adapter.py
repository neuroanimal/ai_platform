"""
Google Gemini adapter via the Gemini API's OpenAI-compatible endpoint
(https://ai.google.dev/gemini-api/docs/openai).

Key from ``GEMINI_API_KEY`` unless configured. ``model`` is required
(e.g. a current "gemini-*" id).

Previously a stub returning a fabricated string; the class name and the
LLMAdapter methods are unchanged.
"""

from ai_platform.common.llm.openai_compatible_adapter import OpenAICompatibleAdapter


class GoogleAdapter(OpenAICompatibleAdapter):
    """Chat Completions adapter for Google Gemini."""

    PROVIDER = "google"
    DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
    # The base URL already contains the version segment.
    DEFAULT_API_PREFIX = ""
    DEFAULT_API_KEY_ENV = "GEMINI_API_KEY"
    REQUIRES_API_KEY = True
