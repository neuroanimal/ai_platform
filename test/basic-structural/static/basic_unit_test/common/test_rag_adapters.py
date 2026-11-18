"""Tests of the RAG adapters.

- NativeRAGAdapter and LangChainRAGAdapter run for real (SQLite vector
  store, HashingEmbedder, langchain-core) with a scripted LLM.
- Haystack, LlamaIndex, txtai and Embedchain run against fake modules that
  implement only the calls the adapters make; RAGFlow against a fake server.
  These prove the adapters' wiring, not compatibility with real releases.
- Canopy and Verba must refuse instead of fabricating.
"""

import importlib.util
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(__file__))

from fake_json_server import FakeJsonServer  # noqa: E402

from ai_platform.common.llm.chat_result import ChatResult  # noqa: E402
from ai_platform.common.rag.canopy_adapter import CanopyAdapter  # noqa: E402
from ai_platform.common.rag.embedchain_adapter import EmbedchainAdapter  # noqa: E402
from ai_platform.common.rag.embedder import HashingEmbedder, OpenAICompatibleEmbedder  # noqa: E402
from ai_platform.common.rag.haystack_rag_adapter import HaystackRAGAdapter  # noqa: E402
from ai_platform.common.rag.langchain_rag_adapter import LangChainRAGAdapter  # noqa: E402
from ai_platform.common.rag.llamaindex_adapter import LlamaIndexAdapter  # noqa: E402
from ai_platform.common.rag.native_rag_adapter import (  # noqa: E402
    NativeRAGAdapter,
    RAGError,
    split_text,
)
from ai_platform.common.rag.ragflow_adapter import RAGFlowAdapter  # noqa: E402
from ai_platform.common.rag.txtai_rag_adapter import TxtaiRAGAdapter  # noqa: E402
from ai_platform.common.rag.verba_adapter import VerbaAdapter  # noqa: E402

DOCS = [
    {"id": "cpi", "text": "Inflacja CPI mierzy zmianę cen koszyka dóbr konsumpcyjnych.",
     "metadata": {"lang": "pl"}},
    {"id": "fx", "text": "Kurs USD/PLN to cena jednego dolara wyrażona w złotych."},
    {"id": "cat", "text": "Mruczek jest kotem, a wszystkie koty są ssakami."},
]
QUESTION = "Co mierzy inflacja CPI?"


class ScriptedLLM:
    """LLM double: records the prompt, answers with a fixed text."""

    def __init__(self, text="Zmianę cen koszyka [1]."):
        self.text = text
        self.prompts = []

    def chat_completion(self, messages, **kwargs):
        """Record and answer."""
        self.prompts.append((messages[0]["content"], kwargs))
        return ChatResult(text=self.text, model="scripted", finish_reason="stop",
                          usage={"total_tokens": 1})


# ----------------------------------------------------------------------------
# chunking and embedder
# ----------------------------------------------------------------------------

def test_split_text_respects_size_and_overlap():
    text = " ".join(f"słowo{i}" for i in range(200))
    chunks = split_text(text, chunk_size=100, overlap=20)
    assert all(len(c) <= 100 for c in chunks)
    assert len(chunks) > 5
    assert chunks[0].split()[-1] in chunks[1]  # overlap keeps the boundary word
    with pytest.raises(RAGError):
        split_text("x", chunk_size=10, overlap=10)


def test_hashing_embedder_is_deterministic_and_lexical():
    emb = HashingEmbedder(64)
    a, b, c = emb.embed(["kot ssak", "kot ssak", "dolar kurs"])
    assert a == b and len(a) == 64
    assert sum(x * y for x, y in zip(a, b)) == pytest.approx(1.0)
    assert sum(x * y for x, y in zip(a, c)) < 0.5


def test_openai_compatible_embedder_against_fake_server():
    def embeddings(_m, _p, body, headers):
        assert headers["authorization"] == "Bearer k"
        return 200, {"data": [{"index": i, "embedding": [float(len(t)), 1.0]}
                              for i, t in reversed(list(enumerate(body["input"])))]}

    with FakeJsonServer({("POST", "/v1/embeddings"): embeddings}) as server:
        vectors = OpenAICompatibleEmbedder(server.url, "e", api_key="k", batch_size=2).embed(
            ["a", "bb", "ccc"])
    assert vectors == [[1.0, 1.0], [2.0, 1.0], [3.0, 1.0]]


# ----------------------------------------------------------------------------
# native and LangChain (real)
# ----------------------------------------------------------------------------

def test_native_rag_retrieves_and_answers_from_context():
    llm = ScriptedLLM()
    rag = NativeRAGAdapter()
    rag.initialize({"llm": llm, "top_k": 2, "max_tokens": 64})
    rag.ingest(DOCS)
    result = rag.query(QUESTION)
    rag.shutdown()

    assert result["stack"] == "native"
    assert result["sources"][0]["document_id"] == "cpi"
    assert result["sources"][0]["metadata"] == {"lang": "pl"}
    assert result["answer"] == llm.text
    prompt, params = llm.prompts[0]
    assert "[1] Inflacja CPI" in prompt and QUESTION in prompt
    assert params == {"max_tokens": 64}


def test_native_rag_without_llm_is_retrieval_only():
    rag = NativeRAGAdapter()
    rag.initialize({})
    rag.ingest(DOCS)
    result = rag.query("Czy Mruczek jest ssakiem?", top_k=1)
    assert result["answer"] is None
    assert result["sources"][0]["document_id"] == "cat"


def test_native_rag_input_validation():
    rag = NativeRAGAdapter()
    with pytest.raises(RAGError):
        rag.ingest(DOCS)
    with pytest.raises(RAGError):
        rag.initialize({"prompt_template": "no placeholders"})
    rag.initialize({})
    with pytest.raises(RAGError):
        rag.ingest([{"text": "  "}])


@pytest.mark.skipif(not importlib.util.find_spec("langchain_core"),
                    reason="langchain-core not installed")
def test_langchain_rag_with_platform_llm():
    llm = ScriptedLLM()
    rag = LangChainRAGAdapter()
    rag.initialize({"llm": llm, "top_k": 1})
    rag.ingest(DOCS)
    result = rag.query(QUESTION)
    assert result["stack"] == "langchain"
    assert result["sources"][0]["document_id"] == "cpi"
    assert result["answer"] == llm.text


@pytest.mark.skipif(not importlib.util.find_spec("langchain_core"),
                    reason="langchain-core not installed")
def test_langchain_rag_with_langchain_chat_model():
    from langchain_core.language_models.fake_chat_models import (  # pylint: disable=import-outside-toplevel
        FakeListChatModel,
    )
    rag = LangChainRAGAdapter()
    rag.initialize({"chat_model": FakeListChatModel(responses=["odp"]), "top_k": 1})
    rag.ingest(DOCS)
    assert rag.query(QUESTION)["answer"] == "odp"


# ----------------------------------------------------------------------------
# framework adapters on fake modules
# ----------------------------------------------------------------------------

def overlap_score(query, text):
    """Word-overlap score used by the fakes."""
    q, t = set(query.lower().split()), set(text.lower().split())
    return len(q & t) / (len(q) or 1)


def test_haystack_adapter_with_fake_module(monkeypatch):
    class Document:
        """Fake haystack.Document."""
        def __init__(self, id=None, content="", meta=None, score=None):  # noqa: A002
            self.id, self.content, self.meta, self.score = id, content, meta or {}, score

    class Store:
        """Fake InMemoryDocumentStore."""
        def __init__(self):
            self.docs = []

        def write_documents(self, docs):
            """Store."""
            self.docs.extend(docs)

    class BM25:
        """Fake InMemoryBM25Retriever."""
        def __init__(self, document_store):
            self.store = document_store

        def run(self, query, top_k):
            """Rank by overlap."""
            ranked = sorted(self.store.docs, key=lambda d: -overlap_score(query, d.content))
            return {"documents": [Document(d.id, d.content, d.meta, overlap_score(query, d.content))
                                  for d in ranked[:top_k]]}

    monkeypatch.setitem(sys.modules, "haystack", types.SimpleNamespace(Document=Document))
    monkeypatch.setitem(sys.modules, "haystack.document_stores.in_memory",
                        types.SimpleNamespace(InMemoryDocumentStore=Store))
    monkeypatch.setitem(sys.modules, "haystack.components.retrievers.in_memory",
                        types.SimpleNamespace(InMemoryBM25Retriever=BM25))
    rag = HaystackRAGAdapter()
    rag.initialize({"llm": ScriptedLLM(), "top_k": 1})
    rag.ingest(DOCS)
    result = rag.query("inflacja CPI mierzy")
    assert result["sources"][0]["document_id"] == "cpi" and result["answer"]


def test_llamaindex_adapter_with_fake_module(monkeypatch):
    class BaseEmbedding:
        """Fake BaseEmbedding: public API calls the private hooks."""
        def __init__(self, model_name=""):
            self.model_name = model_name

    class TextNode:
        """Fake TextNode."""
        def __init__(self, id_, text, metadata):
            self.node_id, self.text, self.metadata = id_, text, metadata

        def get_content(self):
            """Text."""
            return self.text

    class Index:
        """Fake VectorStoreIndex using the wrapped embedder."""
        def __init__(self, nodes, embed_model):
            self.nodes, self.embed = list(nodes), embed_model

        def insert_nodes(self, nodes):
            """Add nodes."""
            self.nodes.extend(nodes)

        def as_retriever(self, similarity_top_k):
            """Retriever over cosine of embeddings."""
            index = self

            class Retriever:
                """Fake retriever."""
                def retrieve(self, query):
                    """Top-k by dot product (vectors are normalized)."""
                    q = index.embed._get_query_embedding(query)  # pylint: disable=protected-access
                    scored = [(sum(a * b for a, b in zip(
                        q, index.embed._get_text_embedding(n.text))), n)  # pylint: disable=protected-access
                        for n in index.nodes]
                    scored.sort(key=lambda s: -s[0])
                    return [types.SimpleNamespace(node=n, score=s)
                            for s, n in scored[:similarity_top_k]]
            return Retriever()

    monkeypatch.setitem(sys.modules, "llama_index.core",
                        types.SimpleNamespace(VectorStoreIndex=Index))
    monkeypatch.setitem(sys.modules, "llama_index.core.embeddings",
                        types.SimpleNamespace(BaseEmbedding=BaseEmbedding))
    monkeypatch.setitem(sys.modules, "llama_index.core.schema",
                        types.SimpleNamespace(TextNode=TextNode))
    rag = LlamaIndexAdapter()
    rag.initialize({"top_k": 1})
    rag.ingest(DOCS)
    assert rag.query(QUESTION)["sources"][0]["document_id"] == "cpi"


def test_txtai_rag_adapter_with_fake_module(monkeypatch):
    class Embeddings:
        """Fake txtai content index with SQL-like search."""
        def __init__(self, config):
            assert config["content"] is True
            self.rows = {}

        def upsert(self, rows):
            """Store rows."""
            for row_id, data, _ in rows:
                self.rows[row_id] = data

        def search(self, sql, limit, parameters):
            """Rank by overlap."""
            assert "similar(:q)" in sql
            ranked = sorted(self.rows.items(),
                            key=lambda kv: -overlap_score(parameters["q"], kv[1]["text"]))
            return [{"id": k, "text": v["text"], "meta_json": v["meta_json"],
                     "score": overlap_score(parameters["q"], v["text"])} for k, v in ranked[:limit]]

    monkeypatch.setitem(sys.modules, "txtai", types.SimpleNamespace(Embeddings=Embeddings))
    rag = TxtaiRAGAdapter()
    rag.initialize({"top_k": 1})
    rag.ingest(DOCS)
    assert rag.query("inflacja CPI mierzy")["sources"][0]["document_id"] == "cpi"


def test_embedchain_adapter_with_fake_app():
    class App:
        """Fake Embedchain App."""
        def __init__(self):
            self.added = []

        def add(self, text, data_type, metadata):
            """Record."""
            assert data_type == "text"
            self.added.append((text, metadata))

        def query(self, question, citations):
            """Answer with the best context."""
            assert citations
            text, meta = max(self.added, key=lambda a: overlap_score(question, a[0]))
            return "odp", [(text, {**meta, "score": 0.9})]

    rag = EmbedchainAdapter()
    rag.initialize({"app": App()})
    rag.ingest(DOCS)
    result = rag.query("inflacja CPI mierzy")
    assert result["answer"] == "odp" and result["sources"][0]["document_id"] == "cpi"


# ----------------------------------------------------------------------------
# RAGFlow fake server
# ----------------------------------------------------------------------------

def test_ragflow_upload_parse_retrieve():
    store = {"docs": {}}

    def create_dataset(*_):
        return 200, {"code": 0, "data": {"id": "ds1"}}

    def upload(_m, _p, body, headers):
        assert headers["content-type"].startswith("multipart/form-data")
        doc_id = f"d{len(store['docs'])}"
        text = body.split(b"\r\n\r\n", 1)[1].rsplit(b"\r\n--", 1)[0].decode()
        store["docs"][doc_id] = text
        return 200, {"code": 0, "data": [{"id": doc_id}]}

    def retrieval(_m, _p, body, _h):
        ranked = sorted(store["docs"].items(), key=lambda kv: -overlap_score(body["question"], kv[1]))
        return 200, {"code": 0, "data": {"chunks": [
            {"id": f"c-{k}", "content": v, "similarity": overlap_score(body["question"], v),
             "document_id": k} for k, v in ranked]}}

    routes = {
        ("POST", "/api/v1/datasets"): create_dataset,
        ("POST", "/api/v1/datasets/ds1/documents"): upload,
        ("POST", "/api/v1/datasets/ds1/chunks"): {"code": 0},
        ("GET", "/api/v1/datasets/ds1/documents?page_size=1024"):
            lambda *a: (200, {"code": 0, "data": {"docs": [
                {"id": k, "run": "DONE"} for k in store["docs"]]}}),
        ("POST", "/api/v1/retrieval"): retrieval,
    }
    with FakeJsonServer(routes) as server:
        rag = RAGFlowAdapter()
        rag.initialize({"url": server.url, "api_key": "k", "llm": ScriptedLLM(), "top_k": 1})
        rag.ingest(DOCS)
        result = rag.query("inflacja CPI mierzy")
    assert result["sources"][0]["text"].startswith("Inflacja CPI")
    assert result["answer"]


def test_ragflow_requires_key(monkeypatch):
    monkeypatch.delenv("RAGFLOW_API_KEY", raising=False)
    with pytest.raises(RAGError):
        RAGFlowAdapter().initialize({})


@pytest.mark.parametrize("cls", [CanopyAdapter, VerbaAdapter])
def test_unmaintained_stacks_refuse(cls):
    with pytest.raises(NotImplementedError, match="NativeRAGAdapter"):
        cls().initialize({})
    with pytest.raises(NotImplementedError):
        cls().query("x")
