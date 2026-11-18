"""LangChain RAG adapter (langchain-core).

Retrieval runs on LangChain primitives - ``Document``,
``InMemoryVectorStore`` (or any LangChain ``VectorStore`` passed in) and an
``Embeddings`` object - and the answer is generated either by a LangChain
chat model or by one of this platform's LLM adapters.

Configuration (on top of NativeRAGAdapter's shared keys):

    embeddings     a LangChain ``Embeddings``; default: the platform
                   ``embedder`` (HashingEmbedder) wrapped as LangChain Embeddings
    vectorstore    a LangChain ``VectorStore``; default InMemoryVectorStore
    chat_model     a LangChain chat model (``.invoke(prompt) -> AIMessage``);
                   used instead of ``llm`` when given
    llm            platform LLMAdapter (as in NativeRAGAdapter)

Chunking is NativeRAGAdapter's ``split_text`` so that results are comparable
across stacks. Previously a stub returning a fabricated answer; the class
name and the RAGAdapter methods are unchanged.
"""

from typing import Any, Dict, List

from ai_platform.common.rag.embedder import HashingEmbedder
from ai_platform.common.rag.native_rag_adapter import NativeRAGAdapter, RAGError


def wrap_embedder(embedder):
    """Expose a platform Embedder through LangChain's Embeddings interface."""
    from langchain_core.embeddings import Embeddings  # pylint: disable=import-outside-toplevel

    class PlatformEmbeddings(Embeddings):
        """LangChain view of a platform embedder."""

        def embed_documents(self, texts: List[str]) -> List[List[float]]:
            """Embed documents."""
            return embedder.embed(texts)

        def embed_query(self, text: str) -> List[float]:
            """Embed a query."""
            return embedder.embed_one(text)

    return PlatformEmbeddings()


class LangChainRAGAdapter(NativeRAGAdapter):
    """RAG on LangChain retrieval primitives."""

    STACK = "langchain"

    def __init__(self):
        super().__init__()
        self.chat_model = None
        self._store = None
        self._document_cls = None

    def _setup(self, config: Dict[str, Any]) -> None:
        try:
            from langchain_core.documents import Document  # pylint: disable=import-outside-toplevel
            from langchain_core.vectorstores import InMemoryVectorStore  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise RAGError("LangChainRAGAdapter requires: pip install langchain-core") from exc
        self._document_cls = Document
        embeddings = config.get("embeddings") or wrap_embedder(
            config.get("embedder") or HashingEmbedder())
        self._store = config.get("vectorstore") or InMemoryVectorStore(embedding=embeddings)
        self.chat_model = config.get("chat_model")

    def ingest(self, documents: List[Dict[str, Any]]) -> None:
        """Chunk documents and add them to the LangChain vector store."""
        self._require()
        texts, metadata = self.chunk_documents(documents)
        if not texts:
            return
        docs = [self._document_cls(page_content=t, metadata=m) for t, m in zip(texts, metadata)]
        self._store.add_documents(docs, ids=[m["id"] for m in metadata])

    def _retrieve(self, question: str, top_k: int) -> List[Dict[str, Any]]:
        pairs = self._store.similarity_search_with_score(question, k=top_k)
        return [self.make_source(doc.metadata.get("id", doc.id), score,
                                 {**doc.metadata, "text": doc.page_content})
                for doc, score in pairs]

    def query(self, question: str, **kwargs) -> Dict[str, Any]:
        """Answer with the LangChain chat model when configured, else as native."""
        if self.chat_model is None:
            return super().query(question, **kwargs)
        sources = self.retrieve(question, kwargs.pop("top_k", None))
        message = self.chat_model.invoke(self.build_prompt(question, sources), **kwargs)
        metadata = getattr(message, "response_metadata", {}) or {}
        return {"stack": self.STACK, "answer": getattr(message, "content", str(message)),
                "sources": sources, "finish_reason": metadata.get("finish_reason"),
                "usage": getattr(message, "usage_metadata", None) or {}}

    def _teardown(self) -> None:
        self._store = None
