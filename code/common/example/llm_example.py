"""Example usage of LLM adapters."""

from code.common.llm.llm_registry import get_registry
from code.common.llm.openai_adapter import OpenAIAdapter
from code.common.llm.anthropic_adapter import AnthropicAdapter
from code.common.llm.google_adapter import GoogleAdapter
from code.common.llm.cohere_adapter import CohereAdapter
from code.common.llm.mistral_adapter import MistralAdapter
from code.common.llm.huggingface_adapter import HuggingFaceAdapter
from code.common.llm.bedrock_adapter import BedrockAdapter
from code.common.llm.azure_openai_adapter import AzureOpenAIAdapter
from code.common.llm.ollama_adapter import OllamaAdapter
from code.common.llm.together_adapter import TogetherAdapter
from code.common.llm.replicate_adapter import ReplicateAdapter
from code.common.llm.qwen_adapter import QwenAdapter
from code.common.llm.phi_adapter import PhiAdapter
from code.common.llm.deepseek_adapter import DeepSeekAdapter
from code.common.llm.grok_adapter import GrokAdapter

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
