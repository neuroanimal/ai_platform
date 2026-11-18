"""
Text embedders used by the RAG adapters.

An embedder turns texts into vectors for a VectorDBAdapter. Three
implementations, from "works anywhere" to "best quality":

- ``HashingEmbedder``: stdlib only, deterministic feature hashing of word
  tokens. It is *lexical* (shared words), not semantic - fine for tests,
  offline tooling and keyword-heavy corpora, not a substitute for a model.
- ``OpenAICompatibleEmbedder``: ``POST /v1/embeddings`` on any
  OpenAI-compatible server (LocalAI, Ollama, vLLM, OpenAI, ...).
- ``SentenceTransformerEmbedder``: local sentence-transformers model,
  imported lazily.
"""

import hashlib
import math
import os
import re
from abc import ABC, abstractmethod
from typing import List, Optional, Sequence

from ai_platform.common.util.http_json_client import HttpJsonClient, HttpJsonError

_TOKEN = re.compile(r"\w+", re.UNICODE)


class EmbeddingError(Exception):
    """An embedder could not produce vectors."""


class Embedder(ABC):
    """Interface: texts in, one vector per text out."""

    @abstractmethod
    def embed(self, texts: Sequence[str]) -> List[List[float]]:
        """Return one vector per input text, in order."""

    def embed_one(self, text: str) -> List[float]:
        """Convenience wrapper for a single text."""
        return self.embed([text])[0]


class HashingEmbedder(Embedder):
    """Deterministic lexical embedder (feature hashing, signed, L2-normalized)."""

    def __init__(self, dimension: int = 512) -> None:
        if dimension < 8:
            raise ValueError("dimension must be >= 8")
        self.dimension = dimension

    def embed(self, texts: Sequence[str]) -> List[List[float]]:
        """Hash lowercase word tokens into a fixed-size vector."""
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> List[float]:
        vector = [0.0] * self.dimension
        for token in _TOKEN.findall(str(text).lower()):
            digest = hashlib.md5(token.encode("utf-8")).digest()  # not security-relevant
            index = int.from_bytes(digest[:4], "little") % self.dimension
            vector[index] += 1.0 if digest[4] & 1 else -1.0
        norm = math.sqrt(sum(x * x for x in vector))
        return [x / norm for x in vector] if norm else vector


class OpenAICompatibleEmbedder(Embedder):
    """Embeddings from an OpenAI-compatible ``/v1/embeddings`` endpoint."""

    def __init__(self, base_url: str, model: str, *, api_key: Optional[str] = None,
                 api_key_env: Optional[str] = None, api_prefix: str = "/v1",
                 timeout: float = 120.0, batch_size: int = 64) -> None:
        key = api_key or (os.environ.get(api_key_env) if api_key_env else None)
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        self._client = HttpJsonClient(base_url, timeout=timeout, headers=headers)
        self.model = model
        self.api_prefix = api_prefix.rstrip("/")
        self.batch_size = batch_size

    def embed(self, texts: Sequence[str]) -> List[List[float]]:
        """Embed in batches; keep the server's ``index`` order."""
        vectors: List[List[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = list(texts[start:start + self.batch_size])
            try:
                data = self._client.post(f"{self.api_prefix}/embeddings",
                                         {"model": self.model, "input": batch}).data
            except HttpJsonError as exc:
                raise EmbeddingError(f"embeddings request failed: {exc}") from exc
            try:
                items = sorted(data["data"], key=lambda item: item.get("index", 0))
                vectors.extend([list(map(float, item["embedding"])) for item in items])
            except (KeyError, TypeError) as exc:
                raise EmbeddingError(f"unexpected embeddings answer: {str(data)[:200]}") from exc
        if len(vectors) != len(texts):
            raise EmbeddingError(f"asked for {len(texts)} embeddings, got {len(vectors)}")
        return vectors


class SentenceTransformerEmbedder(Embedder):
    """Local sentence-transformers model (downloaded on first use if not cached)."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
                 device: Optional[str] = None) -> None:
        try:
            from sentence_transformers import SentenceTransformer  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise EmbeddingError("pip install sentence-transformers") from exc
        self._model = SentenceTransformer(model_name, device=device)

    def embed(self, texts: Sequence[str]) -> List[List[float]]:
        """Encode with normalized embeddings (cosine-ready)."""
        return self._model.encode(list(texts), normalize_embeddings=True).tolist()
