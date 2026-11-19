"""Live integration tests of the local LLM adapters.

Each test is skipped when its server is not running, so the suite is safe
on machines without LocalAI/Ollama. Endpoints and models can be overridden:

    AI_PLATFORM_LOCALAI_URLS   comma-separated, default http://127.0.0.1:8080,http://127.0.0.1:8081
    AI_PLATFORM_LOCALAI_MODEL  default qwen25-05b-localai
    AI_PLATFORM_OLLAMA_URL     default http://127.0.0.1:11434
    AI_PLATFORM_OLLAMA_MODEL   default qwen2.5:0.5b
"""

import os

import pytest

from ai_platform.common.llm.localai_adapter import LocalAIAdapter
from ai_platform.common.llm.ollama_adapter import OllamaAdapter

LOCALAI_URLS = os.environ.get(
    "AI_PLATFORM_LOCALAI_URLS", "http://127.0.0.1:8080,http://127.0.0.1:8081"
).split(",")
LOCALAI_MODEL = os.environ.get("AI_PLATFORM_LOCALAI_MODEL", "qwen25-05b-localai")
OLLAMA_URL = os.environ.get("AI_PLATFORM_OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("AI_PLATFORM_OLLAMA_MODEL", "qwen2.5:0.5b")


def ready(adapter, url, model):
    """Initialize ``adapter`` or skip when the server/model is unavailable."""
    adapter.initialize({"base_url": url, "model": model, "timeout": 300,
                        "temperature": 0, "max_tokens": 32})
    health = adapter.health()
    if not health["reachable"]:
        pytest.skip(f"server not running at {url}")
    if not health["model_available"]:
        pytest.skip(f"model {model!r} not served at {url}: {health.get('models')}")
    return adapter


@pytest.mark.parametrize("url", LOCALAI_URLS)
def test_localai_chat(url):
    llm = ready(LocalAIAdapter(), url, LOCALAI_MODEL)
    result = llm.chat_completion([{"role": "user", "content": "Ile to 2+2? Odpowiedz liczbą."}])
    assert result.text.strip()
    assert result.finish_reason in ("stop", "length")
    llm.shutdown()


def test_ollama_openai_and_native():
    llm = ready(OllamaAdapter(), OLLAMA_URL, OLLAMA_MODEL)
    assert llm.version() != "unknown"
    assert llm.generate("Say OK.").strip()

    native = llm.native_chat_completion(
        [{"role": "user", "content": "Say OK."}], num_ctx=1024
    )
    assert native.text.strip()
    assert native.metrics["total_seconds"] > 0
    assert native.usage["completion_tokens"] > 0
    llm.shutdown()


def test_native_rag_with_local_llm():
    """End to end: SQLite store, HashingEmbedder, a local LocalAI model answering."""
    from ai_platform.common.rag.native_rag_adapter import (  # pylint: disable=import-outside-toplevel
        NativeRAGAdapter,
    )

    llm = ready(LocalAIAdapter(), LOCALAI_URLS[-1], LOCALAI_MODEL)
    llm.default_params["max_tokens"] = 64
    rag = NativeRAGAdapter()
    rag.initialize({"llm": llm, "top_k": 1})
    rag.ingest([
        {"id": "code", "text": "Kod dostępu do magazynu numer 7 to 4512."},
        {"id": "other", "text": "Biuro jest otwarte od 8 do 16."},
    ])
    result = rag.query("Jaki jest kod dostępu do magazynu numer 7?")
    rag.shutdown()
    llm.shutdown()
    assert result["sources"][0]["document_id"] == "code"
    assert "4512" in result["answer"]


EMBED_MODEL = os.environ.get("AI_PLATFORM_OLLAMA_EMBED_MODEL", "bge-m3")


def test_semantic_rag_with_local_embeddings():
    """Cross-lingual retrieval: Polish question, English documents, bge-m3 via Ollama.

    The lexical HashingEmbedder cannot do this (no shared words), so the test
    shows what a real embedding model adds to the native RAG pipeline.
    """
    from ai_platform.common.rag.embedder import (  # pylint: disable=import-outside-toplevel
        EmbeddingError,
        OpenAICompatibleEmbedder,
    )
    from ai_platform.common.rag.native_rag_adapter import (  # pylint: disable=import-outside-toplevel
        NativeRAGAdapter,
    )

    embedder = OpenAICompatibleEmbedder(OLLAMA_URL, EMBED_MODEL)
    try:
        embedder.embed(["probe"])
    except EmbeddingError as exc:
        pytest.skip(f"embedding model {EMBED_MODEL!r} not available at {OLLAMA_URL}: {exc}")

    rag = NativeRAGAdapter()
    rag.initialize({"embedder": embedder, "top_k": 1})
    rag.ingest([
        {"id": "cpi", "text": "Consumer price inflation measures how prices of a basket of "
                              "goods change over time."},
        {"id": "fx", "text": "The USD/PLN exchange rate is the price of one US dollar in "
                             "Polish zloty."},
        {"id": "cat", "text": "Cats are small domesticated carnivorous mammals."},
    ])
    questions = {"Jak mierzy się wzrost cen towarów?": "cpi",
                 "Ile złotych kosztuje dolar?": "fx",
                 "Czy kot jest ssakiem?": "cat"}
    for question, expected in questions.items():
        assert rag.retrieve(question)[0]["document_id"] == expected, question
    rag.shutdown()


@pytest.mark.parametrize("adapter_cls,url,model", [
    (LocalAIAdapter, LOCALAI_URLS[-1], LOCALAI_MODEL),
    (OllamaAdapter, OLLAMA_URL, OLLAMA_MODEL),
])
def test_streaming_live(adapter_cls, url, model):
    from ai_platform.common.llm.openai_compatible_adapter import (  # pylint: disable=import-outside-toplevel
        collect_stream,
    )
    llm = ready(adapter_cls(), url, model)
    chunks = list(llm.stream_chat([{"role": "user", "content": "Policz od 1 do 5."}]))
    llm.shutdown()
    result = collect_stream(iter(chunks))
    assert len(chunks) > 2, "answer arrived in one piece - not streamed"
    assert result.text.strip() and result.finish_reason in ("stop", "length")
