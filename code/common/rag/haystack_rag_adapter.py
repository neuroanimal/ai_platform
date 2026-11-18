"""Haystack RAG adapter (Haystack 2.x, package ``haystack-ai``).

Retrieval uses Haystack's ``InMemoryDocumentStore`` with the
``InMemoryBM25Retriever`` - keyword retrieval that needs no embedding model
- or any document store / retriever pair passed in. Answers are generated
by a platform LLM adapter (``llm``), exactly as in NativeRAGAdapter.

Configuration (on top of NativeRAGAdapter's shared keys):

    document_store   a Haystack document store; default InMemoryDocumentStore
    retriever        a component whose ``run(query=..., top_k=...)`` returns
                     ``{"documents": [...]}``; default InMemoryBM25Retriever

Not verified against an installed Haystack here (the package was not
installed when this was written); unit tests cover the calls through a fake
module. Previously a stub returning a fabricated answer; the class name and
the RAGAdapter methods are unchanged.
"""

from typing import Any, Dict, List

from ai_platform.common.rag.native_rag_adapter import NativeRAGAdapter, RAGError


class HaystackRAGAdapter(NativeRAGAdapter):
    """RAG on a Haystack document store and retriever."""

    STACK = "haystack"

    def __init__(self):
        super().__init__()
        self._store = None
        self._retriever = None
        self._document_cls = None

    def _setup(self, config: Dict[str, Any]) -> None:
        try:
            from haystack import Document  # pylint: disable=import-outside-toplevel
            from haystack.document_stores.in_memory import (  # pylint: disable=import-outside-toplevel
                InMemoryDocumentStore,
            )
            from haystack.components.retrievers.in_memory import (  # pylint: disable=import-outside-toplevel
                InMemoryBM25Retriever,
            )
        except ImportError as exc:
            raise RAGError("HaystackRAGAdapter requires: pip install haystack-ai") from exc
        self._document_cls = Document
        self._store = config.get("document_store") or InMemoryDocumentStore()
        self._retriever = config.get("retriever") or InMemoryBM25Retriever(
            document_store=self._store)

    def ingest(self, documents: List[Dict[str, Any]]) -> None:
        """Chunk documents and write them to the document store."""
        self._require()
        texts, metadata = self.chunk_documents(documents)
        if texts:
            self._store.write_documents([
                self._document_cls(id=m["id"], content=t, meta=m)
                for t, m in zip(texts, metadata)])

    def _retrieve(self, question: str, top_k: int) -> List[Dict[str, Any]]:
        found = self._retriever.run(query=question, top_k=top_k).get("documents", [])
        return [self.make_source(doc.id, doc.score, {**(doc.meta or {}), "text": doc.content})
                for doc in found]

    def _teardown(self) -> None:
        self._store = self._retriever = None
