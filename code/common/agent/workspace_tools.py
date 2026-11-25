"""
Agent skills that work on the local machine: files, an SQLite database, Python code.

Every skill is confined and off unless configured:

- ``file_tools(root)``: ``list_files``, ``read_file``, ``search_files`` inside
  ``root`` only - a path that resolves outside it (``..``, an absolute path,
  a symlink pointing out) is refused. ``write_file`` exists only with
  ``writable=True`` and is marked as a side effect, so an agent runs it only
  when side effects are allowed; it never overwrites unless asked to.
- ``sqlite_tools(db)``: ``list_tables`` and ``query_sqlite`` on a database
  opened READ-ONLY (``mode=ro`` and ``PRAGMA query_only``), with a row cap and
  a time limit per query.
- ``python_tools()``: ``run_python`` executes code in a bubblewrap sandbox:
  no network (``--unshare-all``), no home directory or other files - only
  ``/usr`` read-only and an empty temporary working directory - plus CPU,
  memory and output limits. Without ``bwrap`` installed the tool is not
  offered (``SandboxUnavailable``), rather than running code unconfined.
"""

import fnmatch
import os
import resource
import shutil
import sqlite3
import subprocess
import tempfile
import time
from contextlib import closing
from pathlib import Path
from typing import Any, Dict, List, Optional

from ai_platform.common.agent.tool import Tool

MAX_READ_BYTES = 5_000_000
MAX_SEARCH_FILE_BYTES = 2_000_000
MAX_OUTPUT_CHARS = 10_000


class SandboxUnavailable(Exception):
    """bubblewrap (bwrap) is not installed, so code cannot be run safely."""


def _inside(root: Path, relative: str) -> Path:
    target = (root / relative).resolve()
    if target != root and root not in target.parents:
        raise PermissionError(f"{relative!r} is outside the workspace")
    return target


def _safe(root: Path, item: Path) -> bool:
    """True when ``item`` (e.g. a symlink found while listing) resolves inside ``root``."""
    try:
        _inside(root, item.relative_to(root).as_posix())
        return True
    except (PermissionError, ValueError):
        return False


def _is_text(data: bytes) -> bool:
    return b"\x00" not in data[:8192]


def file_tools(root: Any, writable: bool = False) -> List[Tool]:  # pylint: disable=too-many-locals
    """Read (and optionally write) files under ``root``."""
    base = Path(root).expanduser().resolve()
    if not base.is_dir():
        raise ValueError(f"workspace {base} is not a directory")

    def list_files(path: str = ".", pattern: str = "*", max_entries: int = 200):
        folder = _inside(base, path)
        entries = []
        for item in sorted(folder.rglob("*")):
            if len(entries) >= max_entries:
                break
            relative = item.relative_to(base).as_posix()
            if fnmatch.fnmatch(item.name, pattern) and _safe(base, item):
                entries.append({"path": relative, "dir": item.is_dir(),
                                "bytes": item.stat().st_size if item.is_file() else None})
        return {"root": str(base), "entries": entries, "truncated": len(entries) >= max_entries}

    def read_file(path: str, offset: int = 0, max_chars: int = 20000):
        target = _inside(base, path)
        if target.stat().st_size > MAX_READ_BYTES:
            raise ValueError(f"{path} is larger than {MAX_READ_BYTES} bytes")
        data = target.read_bytes()
        if not _is_text(data):
            raise ValueError(f"{path} is a binary file")
        text = data.decode("utf-8", errors="replace")
        return {"path": path, "chars": len(text), "offset": offset,
                "text": text[offset:offset + max_chars],
                "truncated": offset + max_chars < len(text)}

    def search_files(text: str, pattern: str = "*", max_hits: int = 50):
        needle, hits = text.lower(), []
        for item in sorted(base.rglob("*")):
            if len(hits) >= max_hits:
                break
            if not item.is_file() or not fnmatch.fnmatch(item.name, pattern) \
                    or not _safe(base, item) or item.stat().st_size > MAX_SEARCH_FILE_BYTES:
                continue
            relative = item.relative_to(base).as_posix()
            data = item.read_bytes()
            if not _is_text(data):
                continue
            for number, line in enumerate(data.decode("utf-8", errors="replace").splitlines(), 1):
                if needle in line.lower():
                    hits.append({"path": relative, "line": number, "text": line.strip()[:300]})
                    if len(hits) >= max_hits:
                        break
        return {"hits": hits, "truncated": len(hits) >= max_hits}

    def write_file(path: str, content: str, overwrite: bool = False):
        target = _inside(base, path)
        if target.exists() and not overwrite:
            raise FileExistsError(f"{path} exists; pass overwrite=true to replace it")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"written": path, "chars": len(content)}

    text = {"type": "string"}
    tools = [
        Tool("list_files", f"List files in the user's workspace ({base.name}); paths are "
             "relative to it. pattern is a file-name glob such as *.md.",
             {"type": "object", "properties": {"path": text, "pattern": text,
                                               "max_entries": {"type": "integer", "minimum": 1,
                                                               "maximum": 1000}},
              "additionalProperties": False}, list_files),
        Tool("read_file", "Read a text file of the workspace (relative path).",
             {"type": "object", "properties": {"path": text,
                                               "offset": {"type": "integer", "minimum": 0},
                                               "max_chars": {"type": "integer", "minimum": 1,
                                                             "maximum": 100000}},
              "required": ["path"], "additionalProperties": False}, read_file),
        Tool("search_files", "Find lines containing a text in the workspace files "
             "(case-insensitive); pattern limits the file names, e.g. *.py.",
             {"type": "object", "properties": {"text": text, "pattern": text,
                                               "max_hits": {"type": "integer", "minimum": 1,
                                                            "maximum": 500}},
              "required": ["text"], "additionalProperties": False}, search_files),
    ]
    if writable:
        tools.append(Tool("write_file", "Write a text file in the workspace (refuses to "
                          "overwrite unless overwrite is true).",
                          {"type": "object", "properties": {"path": text, "content": text,
                                                            "overwrite": {"type": "boolean"}},
                           "required": ["path", "content"], "additionalProperties": False},
                          write_file, side_effects=True))
    return tools


def sqlite_tools(db_path: Any, max_rows: int = 200, max_seconds: float = 10.0) -> List[Tool]:
    """Read-only access to one SQLite database."""
    path = Path(db_path).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"database {path} not found")

    def connect() -> sqlite3.Connection:
        conn = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True, timeout=5)
        conn.execute("PRAGMA query_only = ON")
        return conn

    def list_tables():
        with closing(connect()) as conn:
            rows = conn.execute("SELECT name, sql FROM sqlite_master WHERE type IN "
                                "('table', 'view') ORDER BY name").fetchall()
        return [{"name": name, "definition": sql} for name, sql in rows]

    def query_sqlite(sql: str):
        deadline = time.monotonic() + max_seconds
        with closing(connect()) as conn:
            # Returning non-zero from the handler aborts the statement.
            conn.set_progress_handler(lambda: int(time.monotonic() > deadline), 10_000)
            cursor = conn.execute(sql)
            rows = cursor.fetchmany(max_rows + 1)
            columns = [d[0] for d in cursor.description or []]
        return {"columns": columns, "rows": [list(r) for r in rows[:max_rows]],
                "truncated": len(rows) > max_rows}

    return [
        Tool("list_tables", f"Tables and views of the database {path.name}, with their "
             "CREATE statements.", {"type": "object", "properties": {},
                                    "additionalProperties": False}, list_tables),
        Tool("query_sqlite", f"Run one read-only SQL query (SELECT) on {path.name}; returns "
             f"at most {max_rows} rows.",
             {"type": "object", "properties": {"sql": {"type": "string"}},
              "required": ["sql"], "additionalProperties": False}, query_sqlite),
    ]


def bwrap_command(workdir: str, python: str = "/usr/bin/python3") -> List[str]:
    """Sandbox: /usr read-only, empty /tmp, the work dir, no network, no other files."""
    return ["bwrap", "--ro-bind", "/usr", "/usr", "--symlink", "usr/lib", "/lib",
            "--symlink", "usr/lib64", "/lib64", "--symlink", "usr/bin", "/bin",
            "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
            "--bind", workdir, "/work", "--chdir", "/work",
            "--unshare-all", "--die-with-parent", "--new-session",
            "--clearenv", "--setenv", "PATH", "/usr/bin", "--setenv", "HOME", "/work",
            python, "-I", "main.py"]


def python_tools(timeout: float = 20.0, memory_mb: int = 1024) -> List[Tool]:
    """``run_python`` in a bubblewrap sandbox; raises SandboxUnavailable without bwrap."""
    if shutil.which("bwrap") is None:
        raise SandboxUnavailable("bubblewrap (bwrap) is not installed - code is not run "
                                 "without a sandbox")

    def limits() -> None:  # in the child, before bwrap starts
        resource.setrlimit(resource.RLIMIT_AS, (memory_mb << 20, memory_mb << 20))
        resource.setrlimit(resource.RLIMIT_CPU, (int(timeout) + 1, int(timeout) + 1))
        resource.setrlimit(resource.RLIMIT_FSIZE, (50 << 20, 50 << 20))

    def run_python(code: str) -> Dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="ai_platform_sandbox_") as workdir:
            Path(workdir, "main.py").write_text(code, encoding="utf-8")
            start = time.monotonic()
            try:
                done = subprocess.run(bwrap_command(workdir), capture_output=True, text=True,
                                      timeout=timeout, preexec_fn=limits, check=False,
                                      env={"PATH": os.environ.get("PATH", "/usr/bin")})
                result: Dict[str, Any] = {"exit_code": done.returncode,
                                          "stdout": done.stdout[-MAX_OUTPUT_CHARS:],
                                          "stderr": done.stderr[-MAX_OUTPUT_CHARS:]}
            except subprocess.TimeoutExpired as exc:
                result = {"exit_code": None, "timeout": True,
                          "stdout": _text(exc.stdout)[-MAX_OUTPUT_CHARS:],
                          "stderr": f"stopped after {timeout} s"}
            result["seconds"] = round(time.monotonic() - start, 2)
            return result

    return [Tool("run_python", "Run a short Python program and return what it prints. It runs "
                 "in a sandbox: standard library only, no network, no access to the user's "
                 f"files, at most {timeout:g} s. Use print() for the result.",
                 {"type": "object", "properties": {"code": {"type": "string"}},
                  "required": ["code"], "additionalProperties": False}, run_python,
                 metadata={"sandbox": "bubblewrap"})]


def _text(value: Optional[Any]) -> str:
    if value is None:
        return ""
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else str(value)
