# RAG Stack Support

Retrieval-Augmented Generation stack adapters.

## Supported Stacks

- **LlamaIndex**: Data framework for LLM applications
- **LangChain**: RAG chains and retrievers
- **Haystack**: NLP framework with RAG pipelines
- **Verba**: Weaviate's RAG application
- **RAGFlow**: Open-source RAG engine
- **Canopy**: Pinecone's RAG framework
- **Embedchain**: RAG framework with memory
- **txtai**: Semantic search and RAG

## Usage

```python
from code.common.rag.rag_registry import get_registry
from code.common.rag.llamaindex_adapter import LlamaIndexAdapter

registry = get_registry()
registry.register("llamaindex", LlamaIndexAdapter)

rag = registry.get("llamaindex")
rag.initialize({"index_type": "vector"})
rag.ingest([{"text": "Document content"}])
result = rag.query("What is this about?")
print(result["answer"])
rag.shutdown()
```
