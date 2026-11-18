"""
LocalAI adapter (https://localai.io).

LocalAI serves the OpenAI Chat Completions API, so this is the generic
adapter with LocalAI defaults: no API key, default port 8080. A second
instance (e.g. native WSL2 build on 8081 next to the Docker one on 8080)
is selected with ``base_url``.
"""

from ai_platform.common.llm.openai_compatible_adapter import OpenAICompatibleAdapter


class LocalAIAdapter(OpenAICompatibleAdapter):
    """OpenAI-compatible adapter preconfigured for a local LocalAI server."""

    PROVIDER = "localai"
    DEFAULT_BASE_URL = "http://127.0.0.1:8080"
    DEFAULT_API_KEY_ENV = "LOCALAI_API_KEY"
    REQUIRES_API_KEY = False
