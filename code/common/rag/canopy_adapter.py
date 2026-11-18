"""Canopy RAG adapter - not implemented, on purpose.

Canopy (Pinecone's RAG framework, package ``canopy-sdk``) is, to the best of
the author's knowledge, no longer maintained by Pinecone; building on it
would tie this platform to an abandoned dependency.

Instead of returning a fabricated answer (what the earlier stub did), every
method raises ``NotImplementedError`` with this explanation. Equivalent
functionality that does work:

- ``NativeRAGAdapter`` with ``vector_store=PineconeAdapter()`` - the same
  Pinecone index, with this platform's chunking, retrieval and LLM adapters.

The class name is kept so that registries and imports do not break.
"""

from typing import Any, Dict, List

from ai_platform.common.rag.base import RAGAdapter

_MESSAGE = (
    "CanopyAdapter is not implemented: Canopy is no longer maintained. "
    "Use NativeRAGAdapter with {\"vector_store\": PineconeAdapter()} instead."
)


class CanopyAdapter(RAGAdapter):
    """Placeholder that refuses to pretend; see the module docstring."""

    def initialize(self, config: Dict[str, Any]) -> None:
        """Not implemented."""
        raise NotImplementedError(_MESSAGE)

    def ingest(self, documents: List[Dict[str, Any]]) -> None:
        """Not implemented."""
        raise NotImplementedError(_MESSAGE)

    def query(self, question: str, **kwargs) -> Dict[str, Any]:
        """Not implemented."""
        raise NotImplementedError(_MESSAGE)

    def shutdown(self) -> None:
        """Nothing to release."""
