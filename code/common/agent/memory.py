"""
Long-term memory: notes kept in a local SQLite file, found again by meaning or by words.

Nothing leaves the machine. A note is a short text with optional tags and its
origin (``source``: "user" when typed in, "agent" when a model decided to
remember it). Search:

- with an embedder (e.g. ``ollama:bge-m3``): cosine similarity of the note and
  the query embeddings - finds "ile mam ciężarówek" for a note about "flota";
- always also full-text search (SQLite FTS5, BM25 ranking) on the words, which
  works without any model server and catches exact names and numbers.

Results carry ``match`` ("semantic" or "keyword") and a ``score``. Every
operation opens its own connection, so one store can serve several threads
(the chat server's requests). If the embedder is unavailable when a note is
added, the note is stored without an embedding and found by keywords only.

``memory_tools`` exposes the store to the agent: ``remember``, ``recall`` and
``forget``. They change only this store - not files, not other systems - so
they are not marked as side effects.
"""

import json
import math
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ai_platform.common.agent.tool import Tool

DEFAULT_PATH = Path.home() / ".local" / "share" / "ai_platform" / "memory.sqlite"
MAX_NOTE_CHARS = 4000
_WORDS = re.compile(r"\w+", re.UNICODE)

SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_utc TEXT NOT NULL,
    text TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]',
    source TEXT NOT NULL DEFAULT 'user',
    embedding TEXT
);
CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(text, tags);
"""


class MemoryStoreError(Exception):
    """Invalid note or unknown note id."""


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    norm = math.sqrt(sum(a * a for a in left)) * math.sqrt(sum(b * b for b in right))
    return dot / norm if norm else 0.0


class MemoryStore:
    """Notes in SQLite with semantic and keyword search."""

    def __init__(self, path: Any = DEFAULT_PATH, embedder: Any = None) -> None:
        self.path = Path(path).expanduser()
        self.embedder = embedder
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn:
            conn.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _embed(self, text: str) -> Optional[List[float]]:
        if self.embedder is None:
            return None
        try:
            return list(self.embedder.embed([text])[0])
        except Exception:  # pylint: disable=broad-exception-caught
            return None  # model server down: the note is still found by keywords

    def add(self, text: str, tags: Sequence[str] = (), source: str = "user") -> int:
        """Store a note; returns its id."""
        text = str(text or "").strip()
        if not text:
            raise MemoryStoreError("a note needs text")
        if len(text) > MAX_NOTE_CHARS:
            raise MemoryStoreError(f"a note is at most {MAX_NOTE_CHARS} characters")
        tags = [str(t).strip() for t in tags if str(t).strip()]
        embedding = self._embed(text)
        with closing(self._connect()) as conn, conn:  # pylint: disable=confusing-with-statement
            cursor = conn.execute(
                "INSERT INTO notes (created_utc, text, tags, source, embedding) "
                "VALUES (?, ?, ?, ?, ?)",
                (datetime.now(timezone.utc).isoformat(timespec="seconds"), text,
                 json.dumps(tags, ensure_ascii=False), source,
                 json.dumps(embedding) if embedding else None))
            conn.execute("INSERT INTO notes_fts (rowid, text, tags) VALUES (?, ?, ?)",
                         (cursor.lastrowid, text, " ".join(tags)))
            return int(cursor.lastrowid)

    def delete(self, note_id: int) -> None:
        """Remove a note."""
        with closing(self._connect()) as conn, conn:  # pylint: disable=confusing-with-statement
            if conn.execute("DELETE FROM notes WHERE id = ?", (int(note_id),)).rowcount == 0:
                raise MemoryStoreError(f"no note with id {note_id}")
            conn.execute("DELETE FROM notes_fts WHERE rowid = ?", (int(note_id),))

    def list(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Newest notes first."""
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT * FROM notes ORDER BY id DESC LIMIT ?",
                                (int(limit),)).fetchall()
        return [_note(row) for row in rows]

    def count(self) -> int:
        """Number of notes."""
        with closing(self._connect()) as conn:
            return int(conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0])

    def search(self, query: str, limit: int = 5,
               min_score: Optional[float] = None) -> List[Dict[str, Any]]:
        """Best notes for ``query``: semantic hits (score >= ``min_score``), then keyword hits."""
        found: Dict[int, Dict[str, Any]] = {}
        vector = self._embed(query)
        with closing(self._connect()) as conn:
            if vector:
                rows = conn.execute("SELECT * FROM notes WHERE embedding IS NOT NULL").fetchall()
                scored = sorted(((_cosine(vector, json.loads(r["embedding"])), r) for r in rows),
                                key=lambda pair: pair[0], reverse=True)
                for score, row in scored[:limit]:
                    if min_score is None or score >= min_score:
                        found[row["id"]] = {**_note(row), "score": round(score, 3),
                                            "match": "semantic"}
            words = _WORDS.findall(query)
            if words:
                expression = " OR ".join(f'"{w}"' for w in words)
                rows = conn.execute(
                    "SELECT notes.*, bm25(notes_fts) AS rank FROM notes_fts "
                    "JOIN notes ON notes.id = notes_fts.rowid WHERE notes_fts MATCH ? "
                    "ORDER BY rank LIMIT ?", (expression, int(limit))).fetchall()
                for row in rows:
                    found.setdefault(row["id"], {**_note(row), "score": round(-row["rank"], 3),
                                                 "match": "keyword"})
        return list(found.values())[:limit]


def _note(row: sqlite3.Row) -> Dict[str, Any]:
    return {"id": row["id"], "created_utc": row["created_utc"], "text": row["text"],
            "tags": json.loads(row["tags"] or "[]"), "source": row["source"],
            "has_embedding": row["embedding"] is not None}


def memory_tools(store: MemoryStore) -> List[Tool]:
    """remember / recall / forget over ``store`` (changes only the store)."""
    def remember(text: str, tags: Optional[List[str]] = None):
        return {"remembered": store.add(text, tags or [], source="agent")}

    def recall(query: str):
        return [{"id": n["id"], "text": n["text"], "tags": n["tags"], "match": n["match"]}
                for n in store.search(query, limit=5)]

    def forget(note_id: int):
        store.delete(note_id)
        return {"forgotten": note_id}

    return [
        Tool("remember", "Save a short note to the user's long-term memory (facts, preferences, "
             "decisions worth keeping for later conversations).",
             {"type": "object", "properties": {
                 "text": {"type": "string", "description": "the note, one or two sentences"},
                 "tags": {"type": "array", "items": {"type": "string"}}},
              "required": ["text"], "additionalProperties": False}, remember,
             metadata={"changes": "memory store only"}),
        Tool("recall", "Search the user's long-term memory for notes about something.",
             {"type": "object", "properties": {"query": {"type": "string"}},
              "required": ["query"], "additionalProperties": False}, recall),
        Tool("forget", "Delete one note from the user's long-term memory by its id.",
             {"type": "object", "properties": {"note_id": {"type": "integer"}},
              "required": ["note_id"], "additionalProperties": False}, forget,
             metadata={"changes": "memory store only"}),
    ]
