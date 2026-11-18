"""
Hugging Face Inference Providers router, OpenAI-compatible
(https://huggingface.co/docs/inference-providers). Model ids look like
"meta-llama/Llama-3.1-8B-Instruct", optionally suffixed with ":<provider>".

A local Hugging Face TGI server is also OpenAI-compatible: pass its base_url
and require_api_key=False.

Hosted endpoint: needs an API key, read from ``HF_TOKEN`` unless ``api_key`` or
``api_key_env`` is configured. ``model`` has no default on purpose - hosted
model names change faster than this code, so a stale default would fail
silently on the provider side instead of loudly here.

Previously a stub returning a fabricated string; the class name and the
LLMAdapter methods are unchanged.
"""

from ai_platform.common.llm.openai_compatible_adapter import OpenAICompatibleAdapter


class HuggingFaceAdapter(OpenAICompatibleAdapter):
    """Chat Completions adapter for the huggingface hosted API."""

    PROVIDER = "huggingface"
    DEFAULT_BASE_URL = "https://router.huggingface.co"
    DEFAULT_API_PREFIX = "/v1"
    DEFAULT_API_KEY_ENV = "HF_TOKEN"
    REQUIRES_API_KEY = True
