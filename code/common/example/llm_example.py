"""Example usage of LLM adapters."""

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
from ai_platform.common.llm.together_adapter import TogetherAdapter
from ai_platform.common.llm.replicate_adapter import ReplicateAdapter
from ai_platform.common.llm.qwen_adapter import QwenAdapter
from ai_platform.common.llm.phi_adapter import PhiAdapter
from ai_platform.common.llm.deepseek_adapter import DeepSeekAdapter
from ai_platform.common.llm.grok_adapter import GrokAdapter

def main():
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

    for name in llms.keys():
        adapter = registry.get(name)
        adapter.initialize({})
        result = adapter.generate("Hello world")
        print(f"{result}")
        adapter.shutdown()

if __name__ == "__main__":
    main()
