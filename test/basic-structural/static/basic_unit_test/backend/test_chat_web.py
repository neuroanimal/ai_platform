"""Unit tests of the web chat: service (fake models) and HTTP server (no model server needed)."""

import json
import threading
import urllib.error
import urllib.request

import pytest

from ai_platform.backend.service_layer.macro.chat.chat_service import (
    ChatError,
    ChatService,
    Provider,
    load_documents,
    validate_messages,
)
from ai_platform.backend.ui_layer.web.chat_server import create_server, main
from ai_platform.common.llm.chat_result import ChatResult, StreamChunk
from ai_platform.common.llm.llm_exception import LLMConnectionError


class FakeLLM:
    """Streams a fixed answer; records the messages it received."""

    seen = []

    def initialize(self, config):
        """Remember the model."""
        self.model = config["model"]  # pylint: disable=attribute-defined-outside-init

    @staticmethod
    def list_models():
        """Two chat models and one embedding model."""
        return ["tiny:1b", "big:7b", "bge-m3"]

    def stream_chat(self, messages, **_):
        """Answer in two chunks; in the agent's json protocol, as chat_completion would."""
        FakeLLM.seen.append(messages)
        if any("You can use tools" in m["content"] for m in messages if m["role"] == "system"):
            yield StreamChunk(self.chat_completion(messages).text, "stop")
            return
        yield StreamChunk("Odpo")
        yield StreamChunk("wiedź", "stop", {"completion_tokens": 2})

    def chat_completion(self, messages, **_):
        """Agent mode (json protocol): call the calculator once, then answer."""
        if any("returned" in m["content"] for m in messages if m["role"] == "user"):
            return ChatResult(text='{"answer": "391"}', model=self.model)
        return ChatResult(text='{"tool": "calculator", "arguments": {"expression": "17*23"}}',
                          model=self.model)


class DownLLM(FakeLLM):
    """A provider whose server is not running."""

    @staticmethod
    def list_models():
        """Unreachable."""
        raise LLMConnectionError("connection refused")


def make_service(documents="demo:bilingual_qa"):
    """Service with a fake provider, a down provider and the hashing embedder."""
    return ChatService(providers=[Provider("fake", FakeLLM, "http://x"),
                                  Provider("down", DownLLM, "http://y")],
                       documents=documents, embedder="hashing")


def test_models_skip_embeddings_and_unreachable_servers():
    service = make_service()
    assert [m["id"] for m in service.list_models()] == ["fake:big:7b", "fake:tiny:1b"]


def test_validate_messages():
    assert validate_messages([{"role": "user", "content": "x", "extra": 1}]) == \
        [{"role": "user", "content": "x"}]
    for bad in ([], [{"role": "tool", "content": "x"}], [{"role": "assistant", "content": "x"}],
                [{"role": "user", "content": "  "}], "x"):
        with pytest.raises(ChatError):
            validate_messages(bad)


def test_chat_streams_and_rag_adds_sources():
    service = make_service()
    events = list(service.answer({"model": "fake:tiny:1b",
                                  "messages": [{"role": "user", "content": "Ile ciężarówek "
                                                "elektrycznych ma Nordwind?"}]}))
    assert [e["type"] for e in events] == ["context", "delta", "delta", "finish", "done"]
    assert events[0]["context_tokens"] == 4096 and events[0]["dropped_messages"] == 0
    assert "".join(e["text"] for e in events if e["type"] == "delta") == "Odpowiedź"
    events = list(service.answer({"model": "fake:tiny:1b", "use_documents": True,
                                  "messages": [{"role": "user", "content": "Nordwind?"}]}))
    assert events[0]["type"] == "sources" and len(events[0]["sources"]) == 4
    assert FakeLLM.seen[-1][0]["role"] == "system" and "[1]" in FakeLLM.seen[-1][0]["content"]
    assert service.status()["documents"]["indexed"]
    service.close()


def test_agent_mode_reports_trace():
    events = list(make_service().answer({
        "model": "fake:big:7b", "mode": "agent", "agent_mode": "json",
        "messages": [{"role": "user", "content": "17 razy 23?"}]}))
    trace = next(e for e in events if e["type"] == "trace")
    assert trace["tools_used"] == ["calculator"] and trace["stop_reason"] == "answered"
    assert next(e for e in events if e["type"] == "delta")["text"] == "391"


def test_errors_become_events():
    service = make_service(documents=None)
    for request in ({"model": "fake:nope", "messages": [{"role": "user", "content": "x"}]},
                    {"model": "other:x", "messages": [{"role": "user", "content": "x"}]},
                    {"model": "fake:tiny:1b", "use_documents": True,
                     "messages": [{"role": "user", "content": "x"}]}):
        events = list(service.answer(request))
        assert [e["type"] for e in events] == ["error"]


def test_load_documents_from_directory(tmp_path):
    (tmp_path / "a.md").write_text("Ala ma kota.", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("Kot ma Alę.", encoding="utf-8")
    (tmp_path / "c.bin").write_bytes(b"\x00")
    assert [d["id"] for d in load_documents(str(tmp_path))] == ["a.md", "sub/b.txt"]
    with pytest.raises(ChatError):
        load_documents(str(tmp_path / "missing"))


@pytest.fixture(name="server_url")
def fixture_server_url(tmp_path):
    """Running server on a free port with a minimal static directory."""
    (tmp_path / "index.html").write_text("<h1>chat</h1>", encoding="utf-8")
    (tmp_path / "secret.py").write_text("x", encoding="utf-8")
    server = create_server(make_service(), port=0, static_dir=tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def _request(url, data=None, headers=None):
    request = urllib.request.Request(url, data=data, headers=headers or {},
                                     method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.headers.get("Content-Type"), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type"), exc.read()


def test_server_routes(server_url):
    status, ctype, body = _request(server_url + "/")
    assert status == 200 and ctype.startswith("text/html") and b"chat" in body
    for path in ("/static/secret.py", "/static/../index.html", "/static/%2e%2e/x.html", "/nope"):
        assert _request(server_url + path)[0] == 404
    status, _, body = _request(server_url + "/api/models")
    assert status == 200 and len(json.loads(body)["models"]) == 2
    payload = json.dumps({"model": "fake:tiny:1b",
                          "messages": [{"role": "user", "content": "hej"}]}).encode()
    status, ctype, body = _request(server_url + "/api/chat", payload,
                                   {"Content-Type": "application/json"})
    assert status == 200 and ctype.startswith("text/event-stream")
    events = [json.loads(line[5:]) for line in body.decode().splitlines()
              if line.startswith("data:")]
    assert [e["type"] for e in events] == ["context", "delta", "delta", "finish", "done"]


def test_server_rejects_foreign_host_origin_and_form_posts(server_url):
    assert _request(server_url + "/api/models", headers={"Host": "evil.example:80"})[0] == 403
    assert _request(server_url + "/api/models",
                    headers={"Origin": "http://evil.example"})[0] == 403
    assert _request(server_url + "/api/chat", b"model=x",
                    {"Content-Type": "application/x-www-form-urlencoded"})[0] == 415
    assert _request(server_url + "/api/chat", b"[1]", {"Content-Type": "application/json"})[0] \
        == 400


def test_main_refuses_remote_host_without_flag(capsys):
    assert main(["--host", "0.0.0.0"]) == 2
    assert "no authentication" in capsys.readouterr().err


def test_score_floor_and_agent_searches_first():
    from ai_platform.backend.service_layer.macro.chat.chat_service import (  # pylint: disable=import-outside-toplevel
        RAG_NO_MATCH,
    )

    service = ChatService(providers=[Provider("fake", FakeLLM, "http://x")],
                          documents="demo:bilingual_qa", embedder="hashing", min_score=1.01)
    events = list(service.answer({"model": "fake:tiny:1b", "use_documents": True,
                                  "messages": [{"role": "user", "content": "Nordwind?"}]}))
    assert events[0]["sources"] == [] and len(events[0]["below_min_score"]) == 4
    assert FakeLLM.seen[-1][0]["content"] == RAG_NO_MATCH
    service.min_score = None
    events = list(service.answer({"model": "fake:big:7b", "mode": "agent", "agent_mode": "json",
                                  "use_documents": True,
                                  "messages": [{"role": "user", "content": "17 razy 23?"}]}))
    assert [e["type"] for e in events][:3] == ["context", "sources", "trace"]
    service.close()


class LoopingReasoner(FakeLLM):
    """Reasons a little, then loops in the answer."""

    def stream_chat(self, messages, **_):
        """Reasoning, then an endless repetition."""
        FakeLLM.seen.append(messages)
        yield StreamChunk("", reasoning="Myślę...")
        yield StreamChunk("Wynik:")
        while True:
            yield StreamChunk(" razy dwanaście")


def test_chat_streams_reasoning_and_stops_a_loop():
    service = ChatService(providers=[Provider("fake", LoopingReasoner, "http://x")],
                          embedder="hashing")
    events = list(service.answer({"model": "fake:tiny:1b",
                                  "messages": [{"role": "user", "content": "12 x 12?"}]}))
    kinds = [e["type"] for e in events]
    assert kinds[:2] == ["context", "reasoning"] and kinds[-2:] == ["finish", "done"]
    finish = events[-2]
    assert finish["finish_reason"] == "loop" and "dwanaście" in finish["timing"]["loop_unit"]
    assert {"received_utc", "finished_utc"} <= set(events[-1])


def test_long_history_is_summarized_into_the_window():
    class SmallWindow(FakeLLM):
        """Reports a 1024-token window."""

        @staticmethod
        def context_length():
            """Like OllamaAdapter.context_length."""
            return {"effective": 1024, "source": "num_ctx parameter", "trained": 32768}

    history = []
    for number in range(30):
        history += [{"role": "user", "content": f"pytanie {number} " + "x" * 200},
                    {"role": "assistant", "content": f"odpowiedź {number} " + "y" * 200}]
    service = ChatService(providers=[Provider("fake", SmallWindow, "http://x")],
                          embedder="hashing")
    events = list(service.answer({"model": "fake:tiny:1b",
                                  "messages": history + [{"role": "user", "content": "i?"}]}))
    context = events[0]
    assert context["type"] == "context" and context["context_tokens"] == 1024, context
    assert context["dropped_messages"] > 0 and context["summarized"]
    sent = FakeLLM.seen[-1]
    assert sent[0]["content"].startswith("Summary of the earlier part") and sent[-1]["content"] == "i?"


def test_memory_in_chat_and_skills(tmp_path):
    from ai_platform.backend.service_layer.macro.chat.chat_service import (  # pylint: disable=import-outside-toplevel
        Skills,
    )
    from ai_platform.common.agent.memory import MemoryStore  # pylint: disable=import-outside-toplevel

    (tmp_path / "ws").mkdir()
    db = tmp_path / "d.sqlite"
    import sqlite3  # pylint: disable=import-outside-toplevel
    sqlite3.connect(db).close()
    skills = Skills(memory=MemoryStore(tmp_path / "m.sqlite"), workspace=str(tmp_path / "ws"),
                    sqlite=str(db))
    service = ChatService(providers=[Provider("fake", FakeLLM, "http://x")], embedder="hashing",
                          skills=skills)
    note = service.memory_add("Greg ma psa o imieniu Burek")
    assert service.memory_list()["count"] == 1
    events = list(service.answer({"model": "fake:tiny:1b", "use_memory": True,
                                  "messages": [{"role": "user", "content": "Jak ma na imię pies?"}]}))
    memory = next(e for e in events if e["type"] == "memory")
    assert memory["notes"][0]["id"] == note
    assert "Burek" in FakeLLM.seen[-1][0]["content"]
    names = {t.name for t in skills.tools()}
    assert {"remember", "recall", "forget", "list_files", "read_file", "search_files",
            "list_tables", "query_sqlite"} <= names and "write_file" not in names
    assert not skills.allow_side_effects
    assert service.status()["skills"]["workspace"] == str(tmp_path / "ws")
    service.memory_delete(note)
    with pytest.raises(ChatError):
        service.memory_delete(note)
    without = ChatService(providers=[Provider("fake", FakeLLM, "http://x")], embedder="hashing")
    with pytest.raises(ChatError):
        without.memory_list()



def test_memory_routes(tmp_path):
    from ai_platform.backend.service_layer.macro.chat.chat_service import (  # pylint: disable=import-outside-toplevel
        Skills,
    )
    from ai_platform.common.agent.memory import MemoryStore  # pylint: disable=import-outside-toplevel

    service = ChatService(providers=[Provider("fake", FakeLLM, "http://x")], embedder="hashing",
                          skills=Skills(memory=MemoryStore(tmp_path / "m.sqlite")))
    server = create_server(service, port=0, static_dir=tmp_path)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        json_header = {"Content-Type": "application/json"}
        status, _, body = _request(url + "/api/memory", json.dumps({"text": "notatka"}).encode(),
                                   json_header)
        note = json.loads(body)["id"]
        assert status == 200
        assert json.loads(_request(url + "/api/memory")[2])["notes"][0]["text"] == "notatka"
        assert _request(url + "/api/memory", b"text=x",
                        {"Content-Type": "application/x-www-form-urlencoded"})[0] == 415
        assert _request(url + "/api/memory/delete", json.dumps({"id": note}).encode(),
                        json_header)[0] == 200
        assert _request(url + "/api/memory/delete", json.dumps({"id": note}).encode(),
                        json_header)[0] == 400
    finally:
        server.shutdown()
        server.server_close()
