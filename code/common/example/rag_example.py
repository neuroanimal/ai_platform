"""Example usage of RAG stack adapters."""

from ai_platform.common.rag.rag_registry import get_registry
from ai_platform.common.rag.llamaindex_adapter import LlamaIndexAdapter
from ai_platform.common.rag.langchain_rag_adapter import LangChainRAGAdapter
from ai_platform.common.rag.haystack_rag_adapter import HaystackRAGAdapter
from ai_platform.common.rag.verba_adapter import VerbaAdapter
from ai_platform.common.rag.ragflow_adapter import RAGFlowAdapter
from ai_platform.common.rag.canopy_adapter import CanopyAdapter
from ai_platform.common.rag.embedchain_adapter import EmbedchainAdapter
from ai_platform.common.rag.txtai_rag_adapter import TxtaiRAGAdapter

def main():
    registry = get_registry()

    stacks = {
        "llamaindex": LlamaIndexAdapter,
        "langchain": LangChainRAGAdapter,
        "haystack": HaystackRAGAdapter,
        "verba": VerbaAdapter,
        "ragflow": RAGFlowAdapter,
        "canopy": CanopyAdapter,
        "embedchain": EmbedchainAdapter,
        "txtai": TxtaiRAGAdapter,
    }

    for name, adapter_class in stacks.items():
        registry.register(name, adapter_class)

    print(f"Registered {len(stacks)} RAG stacks: {registry.list()}\n")

    for name in stacks.keys():
        adapter = registry.get(name)
        adapter.initialize({})
        adapter.ingest([{"text": "Sample document"}])
        result = adapter.query("What is AI?")
        print(f"{result['stack']}: OK")
        adapter.shutdown()

if __name__ == "__main__":
    main()
