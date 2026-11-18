"""Verba RAG adapter - not implemented, on purpose.

Verba (Weaviate's RAG application, package ``goldenverba``) is an end-user
application with a web UI; it does not offer a documented, stable
programmatic API that an adapter could rely on (none could be confirmed).

Instead of returning a fabricated answer (what the earlier stub did), every
method raises ``NotImplementedError`` with this explanation. Equivalent
functionality that does work:

- ``NativeRAGAdapter`` with ``vector_store=WeaviateAdapter()`` - the same
  Weaviate backend, driven through this platform's ports.

The class name is kept so that registries and imports do not break.
"""

from typing import Any, Dict, List

from ai_platform.common.rag.base import RAGAdapter

_MESSAGE = (
    "VerbaAdapter is not implemented: Verba has no stable programmatic API. "
    "Use NativeRAGAdapter with {\"vector_store\": WeaviateAdapter()} instead."
)


class VerbaAdapter(RAGAdapter):
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
