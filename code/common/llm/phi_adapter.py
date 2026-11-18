"""
Microsoft Phi models adapter.

Phi is a model family, not a hosting service, so this adapter does not pick
a vendor endpoint for you. It is the generic OpenAI-compatible client with
two common setups documented:

- local (Ollama, LocalAI, vLLM, llama.cpp server)::

      PhiAdapter().initialize({"base_url": "http://127.0.0.1:11434",
                               "model": "phi3:mini"})

- Azure AI Foundry serverless endpoint (OpenAI-compatible)::

      PhiAdapter().initialize({"base_url": "https://<endpoint>.models.ai.azure.com",
                               "model": "Phi-4", "api_key_env": "AZURE_AI_API_KEY"})

``base_url`` and ``model`` are therefore required. Previously a stub
returning a fabricated string; the class name and methods are unchanged.
"""

from ai_platform.common.llm.openai_compatible_adapter import OpenAICompatibleAdapter


class PhiAdapter(OpenAICompatibleAdapter):
    """OpenAI-compatible adapter for Phi models served anywhere."""

    PROVIDER = "phi"
    REQUIRES_API_KEY = False
