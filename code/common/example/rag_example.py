"""Example usage of RAG stack adapters."""

# Examples follow the same register-and-try pattern on purpose.
# pylint: disable=duplicate-code

from ai_platform.common.rag.native_rag_adapter import NativeRAGAdapter, RAGError
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
    """Register all RAG stacks and run retrieval with the usable ones."""
    registry = get_registry()

    stacks = {
        "native": NativeRAGAdapter,
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

    documents = [
        {"id": "cpi", "text": "CPI inflation measures the change in consumer prices."},
        {"id": "fx", "text": "The USD/PLN rate is the price of one dollar in zloty."},
    ]

    # Retrieval only (no LLM configured): shows which stacks really work here.
    for name in stacks:
        adapter = registry.get(name)
        try:
            adapter.initialize({"top_k": 1})
            adapter.ingest(documents)
            result = adapter.query("What does CPI measure?")
            top = result["sources"][0] if result["sources"] else {}
            print(f"{name:11} OK      top source: {top.get('document_id')} "
                  f"score={top.get('score')}")
        except (RAGError, NotImplementedError) as exc:
            print(f"{name:11} skipped {type(exc).__name__}: {str(exc)[:80]}")
        finally:
            adapter.shutdown()


if __name__ == "__main__":
    main()
