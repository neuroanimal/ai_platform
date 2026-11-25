"""
Chat service behind the web chat: local models, streaming, documents, tools.

One request = one answer. The client sends the whole conversation each time
(``messages``), so the service keeps no per-user state apart from the shared
document index. Two ways of answering:

- ``chat``: the model's answer is streamed as it is generated. With
  ``use_documents`` the passages retrieved for the last question are put into
  a system message first (RAG) and reported as a ``sources`` event.
- ``agent``: a ``ToolAgent`` answers the last question, calling tools
  (calculator, unit converter, date; with ``use_documents`` also
  ``search_documents``). Not streamed: the full trace of steps and tool
  calls is reported after the run. The agent sees only the last question,
  not the earlier turns - the agent loop takes a single question.

Both yield events (dicts with ``type``): ``sources``, ``reasoning`` (what a
reasoning model thinks, streamed apart from the answer), ``delta`` (text),
``trace`` (agent steps), ``finish`` (finish reason, usage, timestamps), ``done``
(received/finished UTC timestamps, elapsed seconds) or ``error``.

Before a chat answer the conversation is fitted into the model's context
window (``context_window.fit_messages``): system messages and the newest turns
are kept, older turns are replaced by a summary made by the same model, and a
``context`` event reports the estimate. The window is what Ollama will use
(``OllamaAdapter.context_length``; 4096 when the server does not say).

Chat answers are limited by TIME (``max_seconds``, default 300 s), not by a low
token count, and stopped when the model loops (the same phrase repeated
``loop_repeats`` times) - finish reasons "time_limit" and "loop"
(``generation_guard``). The UI layer turns them into Server-Sent Events.

Models come from local, OpenAI-compatible servers (``PROVIDERS``: Ollama and
LocalAI); a model id is ``<provider>:<model>``, e.g. ``ollama:qwen2.5:3b``.
Only models the servers report are accepted, and embedding models are not
offered. No hosted (remote) provider is configured: nothing leaves the machine.

Documents: a fixed corpus chosen when the service is created - the files of a
directory (``.txt`` / ``.md``) or the fictional bilingual QA corpus
("Nordwind", useful for a demo because no model can know its facts). The
client cannot choose a path. The index is built on first use; the SQLite
vector store is bound to the thread that created it, so every index
operation runs on one dedicated worker thread.
"""

import threading
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Sequence

from ai_platform.backend.domain_layer.business_logic.rag_benchmark.qa_sets import get_qa_set
from ai_platform.common.agent.agent_loop import ToolAgent
from ai_platform.common.agent.builtin_tools import default_tools, rag_search_tool
from ai_platform.common.agent.memory import MemoryStore, MemoryStoreError, memory_tools
from ai_platform.common.agent.tool import ToolRegistry
from ai_platform.common.agent.workspace_tools import file_tools, python_tools, sqlite_tools
from ai_platform.common.llm.context_window import (
    ContextError,
    ConversationSummarizer,
    default_reserve,
    fit_messages,
)
from ai_platform.common.llm.generation_guard import LOOP_REPEATS, guarded_chat, guarded_stream
from ai_platform.common.llm.llm_exception import LLMError
from ai_platform.common.llm.localai_adapter import LocalAIAdapter
from ai_platform.common.llm.ollama_adapter import OllamaAdapter
from ai_platform.common.rag.native_rag_adapter import NativeRAGAdapter


@dataclass(frozen=True)
class Provider:
    """A local model server."""

    name: str
    adapter: Callable[[], Any]
    base_url: str


PROVIDERS = (
    Provider("ollama", OllamaAdapter, "http://127.0.0.1:11434"),
    Provider("localai", LocalAIAdapter, "http://127.0.0.1:8081"),
)
#: Substrings of model names that are embedding models, not chat models.
EMBEDDING_MARKERS = ("embed", "bge-")
ROLES = ("system", "user", "assistant")
MODELS_CACHE_SECONDS = 30.0
#: A local model is limited by TIME, not tokens: the answer is stopped after this
#: many seconds (a request may ask for less, or more up to MAX_SECONDS_CAP).
DEFAULT_MAX_SECONDS = 300.0
MAX_SECONDS_CAP = 1800.0
#: Token limit kept only as a backstop (the time budget and loop guard decide).
MAX_TOKENS_BACKSTOP = 16384
#: Context window assumed when the server does not say (Ollama 0.40 default).
DEFAULT_CONTEXT_TOKENS = 4096
#: Time budget for summarizing turns that fall out of the context window.
SUMMARY_SECONDS = 90.0
#: Long conversations are fine: what does not fit the window is summarized
#: (context_window); this only bounds one request (the HTTP body is capped at 1 MB too).
MAX_MESSAGES = 1000
MAX_MESSAGE_CHARS = 20000
MAX_DOCUMENT_BYTES = 2_000_000
DOCUMENT_SUFFIXES = (".txt", ".md")
DEMO_CORPUS = "demo:bilingual_qa"
# The language rule comes last: small models follow the end of a system prompt best,
# and left alone they answer a Polish question about English-free passages in English.
LANGUAGE_RULE = ("Answer in the language of the user's question (Polish question - Polish "
                 "answer). / Odpowiadaj w języku pytania użytkownika.")
#: First version (2026-11-24, kept for reproducing that benchmark): passages
#: are always trusted. Retrieval returns the best match even for a general
#: question, so "Jakie miasto jest stolicą Polski?" got the passage "Kraków was
#: the capital for centuries" and small models answered "Kraków".
RAG_SYSTEM_V1 = ("Answer using the numbered passages below when they are relevant, and say "
                 "which passage you used, e.g. [1]. If they do not contain the answer, say "
                 "so.\n\nPASSAGES:\n{context}\n\n" + LANGUAGE_RULE)
#: Second version: passages may be off-topic; general knowledge is allowed, but
#: facts only the documents can know must come from them.
RAG_SYSTEM = ("Passages retrieved for the user's question are below. They may be irrelevant "
              "or about something else: use only those that answer the question, and cite "
              "them, e.g. [1]. If the question asks about something only these documents "
              "could know (a company, a person, a code, a price) and the passages do not "
              "contain it, say that the documents do not say. If it is general knowledge, "
              "answer from your own knowledge.\n\nPASSAGES:\n{context}\n\n" + LANGUAGE_RULE)
AGENT_SYSTEM = ("Use the calculator for every calculation, even a simple one, with the "
                "numbers taken from the passages or the question - never invented ones.")
#: When no passage reaches the score floor.
RAG_NO_MATCH = ("No document matched the user's question. If it asks about something only "
                "the documents could know (a company, a person, a code, a price), say that "
                "the documents do not say; otherwise answer from your own knowledge.\n\n"
                + LANGUAGE_RULE)
#: Score floor for passages, calibrated for ollama:bge-m3 (cosine) on the
#: bilingual_qa corpus: passages holding the facts scored 0.64 or more (one
#: outlier 0.48), off-topic passages for fact questions at most 0.58, and the
#: misleading "Kraków" passage for the capital question 0.59. Other embedders
#: score differently - set the floor per embedder (None = no floor).
DEFAULT_MIN_SCORE = 0.6


def rag_system_prompt(sources: List[Dict[str, Any]], template: str = RAG_SYSTEM) -> str:
    """System message for ``sources`` (``RAG_NO_MATCH`` when there are none)."""
    if not sources:
        return RAG_NO_MATCH
    context = "\n\n".join(f"[{n}] ({s.get('document_id')}) {s['text']}"
                           for n, s in enumerate(sources, start=1))
    return template.format(context=context)


def split_by_score(sources: List[Dict[str, Any]], min_score: Optional[float]):
    """(passages at or above ``min_score``, passages below it)."""
    if min_score is None:
        return list(sources), []
    used = [s for s in sources if (s.get("score") or 0.0) >= min_score]
    return used, [s for s in sources if s not in used]


class ChatError(Exception):
    """Invalid request (unknown model, malformed messages, no documents)."""


def load_documents(source: str) -> List[Dict[str, Any]]:
    """Documents of ``source``: a directory (``.txt``/``.md``) or ``demo:<qa set>``."""
    if source.startswith("demo:"):
        return [{"id": d.doc_id, "text": d.text} for d in get_qa_set(source[5:]).documents]
    root = Path(source).expanduser()
    if not root.is_dir():
        raise ChatError(f"document directory not found: {root}")
    documents = []
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() in DOCUMENT_SUFFIXES and path.is_file() \
                and path.stat().st_size <= MAX_DOCUMENT_BYTES:
            text = path.read_text(encoding="utf-8", errors="replace")
            if text.strip():
                documents.append({"id": str(path.relative_to(root)), "text": text})
    if not documents:
        raise ChatError(f"no {'/'.join(DOCUMENT_SUFFIXES)} files in {root}")
    return documents


def validate_messages(messages: Any) -> List[Dict[str, str]]:
    """Messages as a clean list; the last one must be the user's question."""
    if not isinstance(messages, list) or not messages:
        raise ChatError("messages must be a non-empty list")
    if len(messages) > MAX_MESSAGES:
        raise ChatError(f"at most {MAX_MESSAGES} messages")
    clean = []
    for message in messages:
        if not isinstance(message, dict) or message.get("role") not in ROLES \
                or not isinstance(message.get("content"), str):
            raise ChatError("every message needs a role (system/user/assistant) and a content")
        if len(message["content"]) > MAX_MESSAGE_CHARS:
            raise ChatError(f"a message is longer than {MAX_MESSAGE_CHARS} characters")
        clean.append({"role": message["role"], "content": message["content"]})
    if clean[-1]["role"] != "user" or not clean[-1]["content"].strip():
        raise ChatError("the last message must be a non-empty user message")
    return clean


class _DocumentIndex:
    """Lazily built RAG index; all operations on one worker thread."""

    def __init__(self, source: Optional[str], embedder: Any, top_k: int) -> None:
        self.source, self.embedder, self.top_k = source, embedder, top_k
        self._worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="chat-index")
        self._rag: Optional[NativeRAGAdapter] = None
        self._documents = 0
        self._lock = threading.Lock()

    def _build(self) -> NativeRAGAdapter:
        documents = load_documents(self.source)
        rag = NativeRAGAdapter()
        rag.initialize({"embedder": self.embedder, "top_k": self.top_k, "chunk_size": 1500,
                        "chunk_overlap": 150})
        rag.ingest(documents)
        self._documents = len(documents)
        return rag

    def _ensure(self) -> NativeRAGAdapter:
        if self._rag is None:
            self._rag = self._build()
        return self._rag

    def retrieve(self, question: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """Best passages for ``question``."""
        if not self.source:
            raise ChatError("the server was started without documents")
        with self._lock:
            return self._worker.submit(
                lambda: self._ensure().retrieve(question, top_k or self.top_k)).result()

    def status(self) -> Dict[str, Any]:
        """Source and whether the index is built."""
        return {"source": self.source, "indexed": self._rag is not None,
                "documents": self._documents}

    def close(self) -> None:
        """Release the index and the worker thread."""
        if self._rag is not None:
            self._worker.submit(self._rag.shutdown).result()
            self._rag = None
        self._worker.shutdown(wait=False)


MEMORY_NOTES = 3


def memory_prompt(notes: List[Dict[str, Any]]) -> str:
    """System message with notes recalled from long-term memory."""
    lines = "\n".join(f"- [note {n['id']}] {n['text']}" for n in notes)
    return ("Notes from the user's long-term memory. They may be unrelated to the question: "
            "use only those that help, and do not mention the others.\n" + lines)


@dataclass
class Skills:
    """Optional agent skills, configured when the server starts (never by a request).

    ``memory``: a MemoryStore (also used in plain chat with "use_memory");
    ``workspace``: a directory the agent may read (``workspace_writable`` lets it
    write there too - a side effect, so the agent is allowed side effects only
    then); ``sqlite``: a database it may query read-only; ``python``: run code
    in the bubblewrap sandbox.
    """

    memory: Optional[MemoryStore] = None
    workspace: Optional[str] = None
    workspace_writable: bool = False
    sqlite: Optional[str] = None
    python: bool = False

    @property
    def allow_side_effects(self) -> bool:
        """Only writing workspace files is a side effect, and only when enabled."""
        return bool(self.workspace and self.workspace_writable)

    def tools(self, include_memory: bool = True) -> List[Any]:
        """Tools of the enabled skills."""
        tools: List[Any] = []
        if self.memory is not None and include_memory:
            tools += memory_tools(self.memory)
        if self.workspace:
            tools += file_tools(self.workspace, writable=self.workspace_writable)
        if self.sqlite:
            tools += sqlite_tools(self.sqlite)
        if self.python:
            tools += python_tools()
        return tools

    def describe(self) -> Dict[str, Any]:
        """Enabled skills, for the status endpoint."""
        return {"memory": str(self.memory.path) if self.memory else None,
                "workspace": self.workspace, "workspace_writable": self.workspace_writable,
                "sqlite": self.sqlite, "python_sandbox": self.python}


class ChatService:  # pylint: disable=too-many-instance-attributes
    """Model listing, streamed chat with optional RAG, and the tool agent."""

    def __init__(self, *, providers: Sequence[Provider] = PROVIDERS,  # pylint: disable=too-many-arguments
                 documents: Optional[str] = None, embedder: Any = "ollama:bge-m3",
                 top_k: int = 4, timeout: float = 600.0,
                 min_score: Optional[float] = None, max_seconds: float = DEFAULT_MAX_SECONDS,
                 loop_repeats: Optional[int] = LOOP_REPEATS,
                 skills: Optional["Skills"] = None) -> None:
        self.providers = {p.name: p for p in providers}
        self.skills = skills or Skills()
        self.timeout = timeout
        self.min_score = min_score
        self.max_seconds = max_seconds
        self.loop_repeats = loop_repeats
        self._contexts: Dict[str, tuple] = {}
        self._summarizers: Dict[str, ConversationSummarizer] = {}
        self._models: List[Dict[str, Any]] = []
        self._models_at = 0.0
        self.index = _DocumentIndex(documents, embedder, top_k)

    # -- models ----------------------------------------------------------------

    def _adapter(self, provider: Provider, model: Optional[str] = None,
                 timeout: Optional[float] = None):
        adapter = provider.adapter()
        adapter.initialize({"base_url": provider.base_url, "model": model or "-",
                            "timeout": timeout or self.timeout})
        return adapter

    def list_models(self, max_age: float = MODELS_CACHE_SECONDS) -> List[Dict[str, Any]]:
        """Chat models of every reachable provider; unreachable ones are skipped.

        Cached for ``max_age`` seconds (0 = ask the servers now).
        """
        if self._models and time.monotonic() - self._models_at < max_age:
            return self._models
        models = []
        for provider in self.providers.values():
            try:
                names = self._adapter(provider, timeout=3).list_models()
            except LLMError:
                continue
            models += [{"id": f"{provider.name}:{name}", "provider": provider.name,
                        "name": name} for name in sorted(names)
                       if not any(m in name.lower() for m in EMBEDDING_MARKERS)]
        self._models, self._models_at = models, time.monotonic()
        return models

    def _llm(self, model_id: str):
        provider_name, _, model = str(model_id).partition(":")
        provider = self.providers.get(provider_name)
        if provider is None or not model:
            raise ChatError(f"unknown model {model_id!r}")
        if model_id not in {m["id"] for m in self.list_models()}:
            raise ChatError(f"model {model_id!r} is not served by {provider_name}")
        return self._adapter(provider, model)

    def context_window(self, model_id: str, llm) -> Dict[str, Any]:
        """Context window of ``model_id`` (cached 30 s; Ollama reports it, else the default)."""
        cached = self._contexts.get(model_id)
        if cached and time.monotonic() - cached[0] < MODELS_CACHE_SECONDS:
            return cached[1]
        info: Dict[str, Any] = {"effective": None, "source": "server default", "trained": None}
        if hasattr(llm, "context_length"):
            try:
                info = llm.context_length()
            except LLMError:
                pass
        info = {**info, "tokens": info.get("effective") or DEFAULT_CONTEXT_TOKENS}
        self._contexts[model_id] = (time.monotonic(), info)
        return info

    def _summarizer(self, model_id: str, llm) -> ConversationSummarizer:
        """Summarizer of dropped turns using ``llm``; its cache lives per model."""
        summarizer = self._summarizers.setdefault(model_id, ConversationSummarizer(str))
        summarizer.complete = lambda prompt: guarded_chat(
            llm, [{"role": "user", "content": prompt}], max_seconds=SUMMARY_SECONDS,
            loop_repeats=self.loop_repeats, max_tokens=600, temperature=0).text
        return summarizer

    def status(self) -> Dict[str, Any]:
        """What the service offers (providers, documents, skills)."""
        return {"providers": list(self.providers), "documents": self.index.status(),
                "skills": self.skills.describe()}

    # -- answering ---------------------------------------------------------------

    def answer(self, request: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        """Events for one request; errors become an ``error`` event."""
        start = time.perf_counter()
        received = _utc()
        try:
            messages = validate_messages(request.get("messages"))
            llm = self._llm(request.get("model", ""))
            params = {"temperature": float(request.get("temperature", 0.3)),
                      "max_tokens": int(request.get("max_tokens", MAX_TOKENS_BACKSTOP))}
            budget = min(float(request.get("max_seconds", self.max_seconds)), MAX_SECONDS_CAP)
            use_documents = bool(request.get("use_documents"))
            use_memory = bool(request.get("use_memory")) and self.skills.memory is not None
            if request.get("mode", "chat") == "agent":
                yield from self._agent(llm, messages[-1]["content"], use_documents,
                                       request.get("agent_mode", "auto"), use_memory)
            else:
                if use_memory:
                    notes = self._memory_notes(messages[-1]["content"])
                    yield {"type": "memory", "notes": notes}
                    if notes:
                        messages = [{"role": "system", "content": memory_prompt(notes)}] + messages
                yield from self._chat(llm, messages, use_documents, params, budget,
                                      request.get("model", ""))
        except (ChatError, LLMError, ValueError) as exc:
            yield {"type": "error", "message": f"{type(exc).__name__}: {exc}",
                   "received_utc": received, "finished_utc": _utc()}
            return
        yield {"type": "done", "elapsed_seconds": round(time.perf_counter() - start, 2),
               "received_utc": received, "finished_utc": _utc()}

    def _chat(self, llm, messages, use_documents, params,  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
              budget, model_id: str = "") -> Iterator[Dict[str, Any]]:
        """Streamed answer under the time budget and the loop guard; reasoning
        (qwen3 and other reasoning models) is streamed as its own events."""
        if use_documents:
            used, dropped = split_by_score(self.index.retrieve(messages[-1]["content"]),
                                           self.min_score)
            yield {"type": "sources", "sources": [_source(s) for s in used],
                   "below_min_score": [_source(s) for s in dropped],
                   "min_score": self.min_score}
            messages = [{"role": "system", "content": rag_system_prompt(used)}] + messages
        window = self.context_window(model_id, llm)
        try:
            messages, report = fit_messages(
                messages, window["tokens"],
                reserve_tokens=default_reserve(window["tokens"], params.get("max_tokens")),
                summarize=self._summarizer(model_id, llm))
        except ContextError as exc:
            raise ChatError(str(exc)) from exc
        yield {"type": "context", **report.to_dict(), "source": window.get("source"),
               "trained": window.get("trained")}
        finish, usage, timing = None, {}, {}
        for chunk in guarded_stream(llm.stream_chat(messages, **params), max_seconds=budget,
                                    loop_repeats=self.loop_repeats, timing=timing):
            if chunk.reasoning:
                yield {"type": "reasoning", "text": chunk.reasoning}
            if chunk.text:
                yield {"type": "delta", "text": chunk.text}
            finish = chunk.finish_reason or finish
            usage = chunk.usage or usage
        yield {"type": "finish", "finish_reason": finish, "usage": usage, "timing": timing,
               "max_seconds": budget}

    def _memory_notes(self, question: str) -> List[Dict[str, Any]]:
        """Notes for a chat answer: semantic hits above the floor; keyword hits only
        when there is no embedder (with one, they are mostly common words)."""
        store = self.skills.memory
        notes = store.search(question, limit=MEMORY_NOTES, min_score=self.min_score)
        if store.embedder is not None:
            notes = [n for n in notes if n["match"] == "semantic"]
        return [{k: n[k] for k in ("id", "text", "tags", "score", "match")} for n in notes]

    def memory_list(self, limit: int = 200) -> Dict[str, Any]:
        """Notes for the memory panel."""
        store = self.skills.memory
        if store is None:
            raise ChatError("the server was started without memory (--memory none)")
        return {"path": str(store.path), "count": store.count(), "notes": store.list(limit)}

    def memory_add(self, text: str, tags=()) -> int:
        """Add a note typed by the user."""
        if self.skills.memory is None:
            raise ChatError("the server was started without memory (--memory none)")
        try:
            return self.skills.memory.add(text, list(tags or []), source="user")
        except MemoryStoreError as exc:
            raise ChatError(str(exc)) from exc

    def memory_delete(self, note_id: int) -> None:
        """Delete a note."""
        if self.skills.memory is None:
            raise ChatError("the server was started without memory (--memory none)")
        try:
            self.skills.memory.delete(int(note_id))
        except (MemoryStoreError, ValueError) as exc:
            raise ChatError(str(exc)) from exc

    def _agent(self, llm, question, use_documents, agent_mode,  # pylint: disable=too-many-arguments,too-many-positional-arguments
               use_memory: bool = False) -> Iterator[Dict[str, Any]]:
        """Tool agent. With documents it searches FIRST: the passages for the
        question are in its system prompt before the first call (the benchmark
        showed small models often never call search_documents themselves), and
        the search tool stays available for follow-up searches. The configured
        skills (memory, workspace files, SQLite, Python sandbox) are its tools."""
        tools = default_tools() + self.skills.tools(include_memory=use_memory)
        system = AGENT_SYSTEM
        if use_documents:
            used, dropped = split_by_score(self.index.retrieve(question), self.min_score)
            yield {"type": "sources", "sources": [_source(s) for s in used],
                   "below_min_score": [_source(s) for s in dropped],
                   "min_score": self.min_score}
            system = rag_system_prompt(used) + "\n\n" + AGENT_SYSTEM
            tools.append(rag_search_tool(self.index))
        run = ToolAgent(llm, ToolRegistry(tools), mode=agent_mode, max_steps=8,
                        system_prompt=system,
                        allow_side_effects=self.skills.allow_side_effects).run(question)
        trace = run.to_dict()
        yield {"type": "trace", "steps": trace["steps"], "tools_used": trace["tools_used"],
               "stop_reason": trace["stop_reason"]}
        if run.answer:
            yield {"type": "delta", "text": run.answer}
        yield {"type": "finish", "finish_reason": run.stop_reason, "usage": {}}

    def close(self) -> None:
        """Release the document index."""
        self.index.close()


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _source(source: Dict[str, Any]) -> Dict[str, Any]:
    score = source.get("score")
    return {"document_id": source.get("document_id"), "text": source.get("text", ""),
            "score": round(float(score), 3) if score is not None else None}
