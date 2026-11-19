"""
Native RAG pipeline: chunk -> embed -> vector store -> retrieve -> LLM.

Built only on this platform's own ports, so every part is replaceable:

    embedder      any ``Embedder`` or a spec string such as "ollama:bge-m3"
                  (default ``HashingEmbedder``)
    vector_store  any ``VectorDBAdapter`` (default in-memory ``SQLiteAdapter``)
    llm           any ``LLMAdapter`` with ``chat_completion`` (optional; without
                  it ``query`` returns retrieval results only, answer = None)

Configuration keys for ``initialize()``:

    embedder, vector_store, llm      instances, see above
    vector_store_config              dict passed to vector_store.connect()
    chunk_size, chunk_overlap        characters, default 800 / 100
    top_k                            passages per question, default 4
    min_score                        drop passages below this score (default none)
    prompt_template                  str with {context} and {question}
    max_tokens, temperature          forwarded to the LLM

Documents for ``ingest()``: ``{"text": str, "id"?: str, "metadata"?: dict}``.
``query()`` returns::

    {"stack": "native", "answer": str | None, "sources": [
        {"id", "document_id", "score", "text", "metadata"}], "finish_reason", "usage"}
"""

import re
from typing import Any, Dict, List, Optional

from ai_platform.common.rag.base import RAGAdapter
from ai_platform.common.rag.embedder import Embedder, HashingEmbedder, create_embedder

DEFAULT_PROMPT = (
    "Answer the question using only the context below. If the context does "
    "not contain the answer, say that you do not know. Cite passages as [n].\n\n"
    "Context:\n{context}\n\nQuestion: {question}\nAnswer:"
)


class RAGError(Exception):
    """RAG pipeline misuse or failure."""


def split_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """Split text into chunks of at most ``chunk_size`` chars on whitespace.

    Consecutive chunks share about ``overlap`` characters so that a sentence
    cut at a boundary is still retrievable from one side.
    """
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise RAGError("need chunk_size > 0 and 0 <= chunk_overlap < chunk_size")
    text = re.sub(r"[ \t]+", " ", str(text)).strip()
    if len(text) <= chunk_size:
        return [text] if text else []

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            cut = max(text.rfind(" ", start, end), text.rfind("\n", start, end))
            if cut > start + chunk_size // 2:
                end = cut
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if c]


class NativeRAGAdapter(RAGAdapter):
    """RAG over the platform's embedder, vector store and LLM ports."""

    STACK = "native"

    def __init__(self) -> None:
        self.initialized = False
        self.embedder: Optional[Embedder] = None
        self.vector_store = None
        self.llm = None
        self.settings: Dict[str, Any] = {}
        self._chunks = 0

    def initialize(self, config: Dict[str, Any]) -> None:
        """Read the shared settings, then let the backend set itself up."""
        config = dict(config or {})
        self.llm = config.get("llm")
        self.settings = {
            "chunk_size": int(config.get("chunk_size", 800)),
            "chunk_overlap": int(config.get("chunk_overlap", 100)),
            "top_k": int(config.get("top_k", 4)),
            "min_score": config.get("min_score"),
            "prompt_template": config.get("prompt_template", DEFAULT_PROMPT),
            "llm_params": {k: config[k] for k in ("max_tokens", "temperature") if k in config},
        }
        if "{context}" not in self.settings["prompt_template"] or \
                "{question}" not in self.settings["prompt_template"]:
            raise RAGError("prompt_template needs {context} and {question}")
        self._chunks = 0
        self._setup(config)
        self.initialized = True

    def _setup(self, config: Dict[str, Any]) -> None:
        """Backend hook: wire the embedder and connect the vector store."""
        embedder = config.get("embedder") or HashingEmbedder()
        # A string is an embedder spec, e.g. "ollama:bge-m3" (see create_embedder).
        self.embedder = create_embedder(embedder) if isinstance(embedder, str) else embedder
        self.vector_store = config.get("vector_store")
        if self.vector_store is None:
            from ai_platform.common.vectordb.sqlite_adapter import (  # pylint: disable=import-outside-toplevel
                SQLiteAdapter,
            )
            self.vector_store = SQLiteAdapter()
        self.vector_store.connect({"metric": "cosine", **config.get("vector_store_config", {})})

    def chunk_documents(self, documents: List[Dict[str, Any]]):
        """Validate and chunk documents; return (texts, metadata) lists.

        Metadata of each chunk: the document's metadata plus ``id``
        ("<document_id>#<n>"), ``document_id`` and ``text``.
        """
        texts, metadata = [], []
        for number, document in enumerate(documents):
            if not isinstance(document, dict) or not str(document.get("text", "")).strip():
                raise RAGError(f"document {number} needs a non-empty 'text'")
            document_id = str(document.get("id", f"doc{self._chunks}-{number}"))
            pieces = split_text(document["text"], self.settings["chunk_size"],
                                self.settings["chunk_overlap"])
            for part, piece in enumerate(pieces):
                texts.append(piece)
                metadata.append({**document.get("metadata", {}), "id": f"{document_id}#{part}",
                                 "document_id": document_id, "text": piece})
        self._chunks += len(texts)
        return texts, metadata

    @staticmethod
    def make_source(chunk_id: Any, score: float, meta: Dict[str, Any]) -> Dict[str, Any]:
        """Build one entry of ``sources`` from chunk metadata."""
        meta = dict(meta or {})
        return {"id": str(chunk_id), "document_id": meta.pop("document_id", None),
                "score": float(score) if score is not None else None,
                "text": meta.pop("text", ""),
                "metadata": {k: v for k, v in meta.items() if k != "id"}}

    def ingest(self, documents: List[Dict[str, Any]]) -> None:
        """Chunk, embed and store documents."""
        self._require()
        texts, metadata = self.chunk_documents(documents)
        if texts:
            self.vector_store.insert(self.embedder.embed(texts), metadata)

    def retrieve(self, question: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return the best passages for ``question`` (score floor applied)."""
        self._require()
        sources = self._retrieve(question, top_k or self.settings["top_k"])
        floor = self.settings["min_score"]
        return [s for s in sources if floor is None or (s["score"] or 0) >= floor]

    def _retrieve(self, question: str, top_k: int) -> List[Dict[str, Any]]:
        """Backend hook: nearest chunks as ``make_source`` dicts."""
        hits = self.vector_store.search(self.embedder.embed_one(question), top_k)
        return [self.make_source(h["id"], h["score"], h["metadata"]) for h in hits]

    def build_prompt(self, question: str, sources: List[Dict[str, Any]]) -> str:
        """Fill the prompt template with numbered passages."""
        context = "\n\n".join(f"[{n}] {s['text']}" for n, s in enumerate(sources, start=1))
        return self.settings["prompt_template"].format(context=context or "(none)",
                                                       question=question)

    def query(self, question: str, **kwargs) -> Dict[str, Any]:
        """Retrieve passages and, when an LLM is configured, answer from them."""
        sources = self.retrieve(question, kwargs.pop("top_k", None))
        result = {"stack": self.STACK, "answer": None, "sources": sources,
                  "finish_reason": None, "usage": {}}
        if self.llm is None:
            return result
        completion = self.llm.chat_completion(
            [{"role": "user", "content": self.build_prompt(question, sources)}],
            **{**self.settings["llm_params"], **kwargs})
        result.update(answer=completion.text, finish_reason=completion.finish_reason,
                      usage=completion.usage)
        return result

    def shutdown(self) -> None:
        """Release the backend; the LLM belongs to the caller."""
        if self.initialized:
            self._teardown()
        self.initialized = False

    def _teardown(self) -> None:
        """Backend hook: disconnect the vector store."""
        if self.vector_store is not None:
            self.vector_store.disconnect()

    def _require(self) -> None:
        if not self.initialized:
            raise RAGError(f"{type(self).__name__} is not initialized")
