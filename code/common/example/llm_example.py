"""Example usage of LLM adapters.

Registers every adapter, then calls only those that can actually answer:
local servers that are running, and hosted providers whose API key is set
in the environment. Nothing is fabricated - an adapter that cannot answer
is reported as skipped with the reason.

    python -m ai_platform.common.example.llm_example
"""

# Examples follow the same register-and-try pattern on purpose.
# pylint: disable=duplicate-code

import os

from ai_platform.common.llm.llm_exception import LLMError
from ai_platform.common.llm.llm_registry import get_registry
from ai_platform.common.llm.openai_adapter import OpenAIAdapter
from ai_platform.common.llm.anthropic_adapter import AnthropicAdapter
from ai_platform.common.llm.google_adapter import GoogleAdapter
from ai_platform.common.llm.cohere_adapter import CohereAdapter
from ai_platform.common.llm.mistral_adapter import MistralAdapter
from ai_platform.common.llm.huggingface_adapter import HuggingFaceAdapter
from ai_platform.common.llm.bedrock_adapter import BedrockAdapter
from ai_platform.common.llm.azure_openai_adapter import AzureOpenAIAdapter
from ai_platform.common.llm.ollama_adapter import OllamaAdapter
from ai_platform.common.llm.localai_adapter import LocalAIAdapter
from ai_platform.common.llm.together_adapter import TogetherAdapter
from ai_platform.common.llm.replicate_adapter import ReplicateAdapter
from ai_platform.common.llm.qwen_adapter import QwenAdapter
from ai_platform.common.llm.phi_adapter import PhiAdapter
from ai_platform.common.llm.deepseek_adapter import DeepSeekAdapter
from ai_platform.common.llm.grok_adapter import GrokAdapter

# Per adapter: configuration for this example. Hosted models are read from
# environment variables so that no model name goes stale in the code.
CONFIGS = {
    "ollama": {"model": os.environ.get("OLLAMA_MODEL", "qwen2.5:0.5b")},
    "localai": {"model": os.environ.get("LOCALAI_MODEL", "qwen25-05b-localai")},
    "phi": {"base_url": os.environ.get("PHI_BASE_URL", "http://127.0.0.1:11434"),
            "model": os.environ.get("PHI_MODEL", "phi3:mini")},
    "openai": {"model": os.environ.get("OPENAI_MODEL")},
    "anthropic": {"model": os.environ.get("ANTHROPIC_MODEL")},
    "google": {"model": os.environ.get("GEMINI_MODEL")},
    "cohere": {"model": os.environ.get("COHERE_MODEL")},
    "mistral": {"model": os.environ.get("MISTRAL_MODEL")},
    "huggingface": {"model": os.environ.get("HF_MODEL")},
    "bedrock": {"model": os.environ.get("BEDROCK_MODEL")},
    "azure_openai": {"base_url": os.environ.get("AZURE_OPENAI_ENDPOINT"),
                     "deployment": os.environ.get("AZURE_OPENAI_DEPLOYMENT")},
    "together": {"model": os.environ.get("TOGETHER_MODEL")},
    "replicate": {"model": os.environ.get("REPLICATE_MODEL")},
    "qwen": {"model": os.environ.get("QWEN_MODEL")},
    "deepseek": {"model": os.environ.get("DEEPSEEK_MODEL")},
    "grok": {"model": os.environ.get("GROK_MODEL")},
}


def main():
    """Register all adapters and query the ones that are usable here."""
    registry = get_registry()

    llms = {
        "openai": OpenAIAdapter,
        "anthropic": AnthropicAdapter,
        "google": GoogleAdapter,
        "cohere": CohereAdapter,
        "mistral": MistralAdapter,
        "huggingface": HuggingFaceAdapter,
        "bedrock": BedrockAdapter,
        "azure_openai": AzureOpenAIAdapter,
        "ollama": OllamaAdapter,
        "localai": LocalAIAdapter,
        "together": TogetherAdapter,
        "replicate": ReplicateAdapter,
        "qwen": QwenAdapter,
        "phi": PhiAdapter,
        "deepseek": DeepSeekAdapter,
        "grok": GrokAdapter,
    }

    for name, adapter_class in llms.items():
        registry.register(name, adapter_class)

    print(f"Registered {len(llms)} LLMs: {registry.list()}\n")

    for name in llms:
        config = {k: v for k, v in CONFIGS.get(name, {}).items() if v}
        config.setdefault("max_tokens", 32)
        adapter = registry.get(name)
        try:
            adapter.initialize(config)
            result = adapter.generate("Hello world")
            print(f"{name:13} OK      {result.strip()[:60]!r}")
        except LLMError as exc:
            print(f"{name:13} skipped {type(exc).__name__}: {str(exc)[:90]}")
        finally:
            adapter.shutdown()


if __name__ == "__main__":
    main()
