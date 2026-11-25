"""Unit tests of the agent skills: memory, workspace files, read-only SQLite, Python sandbox."""

import shutil
import sqlite3

import pytest

from ai_platform.common.agent.memory import MemoryStore, MemoryStoreError, memory_tools
from ai_platform.common.agent.workspace_tools import (
    SandboxUnavailable,
    file_tools,
    python_tools,
    sqlite_tools,
)
from ai_platform.common.rag.embedder import HashingEmbedder


def _tools(tools):
    return {t.name: t for t in tools}


def test_memory_add_search_delete(tmp_path):
    store = MemoryStore(tmp_path / "m.sqlite", embedder=HashingEmbedder())
    first = store.add("Flota Nordwind ma 41 ciężarówek", ["nordwind"])
    store.add("Greg woli odpowiedzi po polsku", ["preferencje"])
    hits = store.search("ciężarówek Nordwind")
    assert hits[0]["id"] == first and hits[0]["match"] in ("semantic", "keyword")
    assert [n["id"] for n in store.search("polsku")][:1] != [first]
    store.delete(first)
    assert store.count() == 1 and all(n["id"] != first for n in store.search("Nordwind"))
    with pytest.raises(MemoryStoreError):
        store.delete(first)
    with pytest.raises(MemoryStoreError):
        store.add("   ")


def test_memory_without_embedder_uses_keywords(tmp_path):
    store = MemoryStore(tmp_path / "m.sqlite")
    note = store.add("Kod do drzwi to 4512")
    hits = store.search("jaki kod?")
    assert hits[0]["id"] == note and hits[0]["match"] == "keyword"
    assert not hits[0]["has_embedding"]


def test_memory_tools(tmp_path):
    tools = _tools(memory_tools(MemoryStore(tmp_path / "m.sqlite")))
    saved = tools["remember"].call({"text": "Spotkanie w piątek o 10"}).content["remembered"]
    assert tools["recall"].call({"query": "piątek"}).content[0]["id"] == saved
    assert tools["forget"].call({"note_id": saved}).ok
    assert not tools["remember"].side_effects


def test_file_tools_stay_inside_the_workspace(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("Ala ma kota\nKot ma Alę\n", encoding="utf-8")
    (tmp_path / "bin.dat").write_bytes(b"\x00\x01")
    outside = tmp_path.parent / "secret_outside.txt"
    outside.write_text("secret", encoding="utf-8")
    (tmp_path / "link.txt").symlink_to(outside)
    tools = _tools(file_tools(tmp_path))
    assert "write_file" not in tools
    listed = [e["path"] for e in tools["list_files"].call({}).content["entries"]]
    assert "docs/a.md" in listed and "link.txt" not in listed
    assert tools["read_file"].call({"path": "docs/a.md"}).content["text"].startswith("Ala")
    for bad in ("../secret_outside.txt", "/etc/passwd", "link.txt"):
        result = tools["read_file"].call({"path": bad})
        assert not result.ok and "outside" in result.error
    assert not tools["read_file"].call({"path": "bin.dat"}).ok
    hits = tools["search_files"].call({"text": "kot"}).content["hits"]
    assert [h["line"] for h in hits] == [1, 2]
    writable = _tools(file_tools(tmp_path, writable=True))
    assert writable["write_file"].side_effects
    assert writable["write_file"].call({"path": "new/x.txt", "content": "hej"}).ok
    assert not writable["write_file"].call({"path": "new/x.txt", "content": "again"}).ok
    outside.unlink()


def test_sqlite_tools_are_read_only(tmp_path):
    db = tmp_path / "d.sqlite"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE t (n INTEGER)")
        conn.executemany("INSERT INTO t VALUES (?)", [(i,) for i in range(300)])
    tools = _tools(sqlite_tools(db, max_rows=100))
    assert tools["list_tables"].call({}).content[0]["name"] == "t"
    result = tools["query_sqlite"].call({"sql": "SELECT n FROM t"}).content
    assert len(result["rows"]) == 100 and result["truncated"]
    for sql in ("DELETE FROM t", "DROP TABLE t", "INSERT INTO t VALUES (1)"):
        assert not tools["query_sqlite"].call({"sql": sql}).ok
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 300


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap not installed")
def test_python_sandbox_has_no_network_and_no_home():
    run = python_tools(timeout=10)[0]
    assert run.call({"code": "print(17 * 23)"}).content["stdout"].strip() == "391"
    probe = ("import os, socket\n"
             "print(os.path.exists(os.path.expanduser('~estagrz')), os.listdir('/'))\n"
             "try:\n    socket.create_connection(('1.1.1.1', 80), timeout=2); print('NET')\n"
             "except OSError:\n    print('no-net')\n")
    out = run.call({"code": probe}).content["stdout"]
    assert "no-net" in out and "home" not in out and "NET\n" not in out
    slow = python_tools(timeout=2)[0].call({"code": "while True: pass"}).content
    assert slow.get("timeout") or slow["exit_code"] != 0


def test_python_tool_refuses_without_bwrap(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    with pytest.raises(SandboxUnavailable):
        python_tools()
