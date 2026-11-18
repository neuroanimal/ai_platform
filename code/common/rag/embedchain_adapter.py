"""Embedchain RAG adapter.

Embedchain bundles chunking, embedding, storage and answering in its
``App``; this adapter maps the RAGAdapter interface onto it:

    ingest  -> App.add(text, data_type="text", metadata=...)
    query   -> App.query(question, citations=True) -> (answer, contexts)

Configuration:

    app_config   dict passed to ``App.from_config(config=...)`` (LLM,
                 embedder and vector DB of Embedchain's own choosing; its
                 defaults call OpenAI and need OPENAI_API_KEY)
    app          an already built Embedchain App (tests, custom setups)

Embedchain's development moved to the mem0 project; this adapter targets
the last ``embedchain`` releases and is not verified against an installed
package here. Previously a stub returning a fabricated answer; the class
name and the RAGAdapter methods are unchanged.
"""

from typing import Any, Dict, List

from ai_platform.common.rag.base import RAGAdapter
from ai_platform.common.rag.native_rag_adapter import RAGError


class EmbedchainAdapter(RAGAdapter):
    """RAG through an Embedchain App."""

    STACK = "embedchain"

    def __init__(self):
        self.initialized = False
        self._app = None

    def initialize(self, config: Dict[str, Any]) -> None:
        """Build the Embedchain App."""
        config = dict(config or {})
        self._app = config.get("app")
        if self._app is None:
            try:
                from embedchain import App  # pylint: disable=import-outside-toplevel
            except ImportError as exc:
                raise RAGError("EmbedchainAdapter requires: pip install embedchain") from exc
            self._app = App.from_config(config=config.get("app_config", {}))
        self.initialized = True

    def ingest(self, documents: List[Dict[str, Any]]) -> None:
        """Add each document's text with its metadata."""
        self._require()
        for number, document in enumerate(documents):
            text = str(document.get("text", "")).strip()
            if not text:
                raise RAGError(f"document {number} needs a non-empty 'text'")
            meta = {**document.get("metadata", {}), "document_id": str(document.get("id", number))}
            self._app.add(text, data_type="text", metadata=meta)

    def query(self, question: str, **kwargs) -> Dict[str, Any]:
        """Ask the App; contexts become ``sources``."""
        self._require()
        answer, contexts = self._app.query(question, citations=True, **kwargs)
        sources = []
        for context in contexts or []:
            text, meta = (context if isinstance(context, (tuple, list)) else (context, {}))
            meta = dict(meta or {})
            sources.append({"id": str(meta.get("doc_id", meta.get("hash", ""))),
                            "document_id": meta.get("document_id"),
                            "score": meta.get("score"), "text": text, "metadata": meta})
        return {"stack": self.STACK, "answer": answer, "sources": sources,
                "finish_reason": None, "usage": {}}

    def shutdown(self) -> None:
        """Drop the App."""
        self._app = None
        self.initialized = False

    def _require(self) -> None:
        if not self.initialized:
            raise RAGError("EmbedchainAdapter is not initialized")
