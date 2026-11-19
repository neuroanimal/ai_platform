"""
Run external command-line tools safely.

Used by adapters that drive desktop/CLI programs (LaTeX, Inkscape,
ImageMagick, FFmpeg, Octave, ...). Rules enforced here:

- commands are argument lists, never shell strings (no ``shell=True``), so
  file names and user values cannot inject shell syntax;
- the executable is resolved with ``shutil.which`` first, so a missing
  tool fails with ``ToolNotFoundError`` naming it, not with a cryptic
  ``FileNotFoundError`` from the OS;
- a timeout is always applied;
- on a non-zero exit, ``ToolFailedError`` carries the tail of stderr.

Adapters accept an injectable ``runner`` (same signature as ``run_tool``)
so their command construction can be unit-tested without the tool.
"""

import shutil
import subprocess
from dataclasses import dataclass
from typing import Mapping, Optional, Sequence


class ToolError(Exception):
    """Base class of external tool errors."""


class ToolNotFoundError(ToolError):
    """None of the candidate executables is on PATH."""

    def __init__(self, candidates: Sequence[str], hint: str = "") -> None:
        names = ", ".join(candidates)
        suffix = f" ({hint})" if hint else ""
        super().__init__(f"external tool not found on PATH: {names}{suffix}")
        self.candidates = list(candidates)


class ToolFailedError(ToolError):
    """The tool exited with a non-zero status or timed out."""

    def __init__(self, command: Sequence[str], returncode: Optional[int], stderr: str) -> None:
        status = "timed out" if returncode is None else f"exit status {returncode}"
        super().__init__(f"{command[0]} failed ({status}): {stderr[-1500:]}")
        self.command = list(command)
        self.returncode = returncode
        self.stderr = stderr


@dataclass
class ToolResult:
    """Completed tool run."""

    command: Sequence[str]
    returncode: int
    stdout: str
    stderr: str


def find_tool(candidates: Sequence[str], hint: str = "") -> str:
    """Return the path of the first candidate found on PATH."""
    for name in candidates:
        path = shutil.which(name)
        if path:
            return path
    raise ToolNotFoundError(candidates, hint)


def run_tool(command: Sequence[str], timeout: float = 300.0, cwd: Optional[str] = None,
             env: Optional[Mapping[str, str]] = None, stdin: Optional[str] = None) -> ToolResult:
    """Run ``command`` (argument list) and return its output; raise on failure."""
    command = [str(part) for part in command]
    try:
        completed = subprocess.run(  # noqa: S603 - argument list, no shell
            command, cwd=cwd, env=dict(env) if env is not None else None, input=stdin,
            capture_output=True, text=True, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ToolFailedError(command, None, str(exc.stderr or "")) from exc
    except FileNotFoundError as exc:
        raise ToolNotFoundError([command[0]]) from exc
    if completed.returncode != 0:
        raise ToolFailedError(command, completed.returncode,
                              completed.stderr or completed.stdout)
    return ToolResult(command, completed.returncode, completed.stdout, completed.stderr)


class CLIToolMixin:  # pylint: disable=too-few-public-methods
    """Common configuration of adapters that drive one external program.

    Subclasses set ``TOOLS`` (candidate executable names, first found wins),
    ``HINT`` (install hint), ``DEFAULT_TIMEOUT`` and ``ERROR`` (the adapter
    family's exception class). ``_configure_cli(config)`` reads ``timeout``,
    ``runner`` (tests) and ``executable`` (explicit path) and locates the
    tool; ``_run_cli(command)`` runs it and translates ``ToolError``.
    """

    TOOLS: Sequence[str] = ()
    HINT = ""
    DEFAULT_TIMEOUT = 120.0
    ERROR = ToolError

    executable: Optional[str] = None
    timeout: float = 120.0
    runner = staticmethod(run_tool)

    def _configure_cli(self, config: Optional[Mapping]) -> None:
        config = dict(config or {})
        self.timeout = float(config.get("timeout", self.DEFAULT_TIMEOUT))
        self.runner = config.get("runner", run_tool)
        try:
            self.executable = config.get("executable") or find_tool(self.TOOLS, self.HINT)
        except ToolError as exc:
            raise self.ERROR(str(exc)) from exc

    def _run_cli(self, command: Sequence[str], **kwargs) -> ToolResult:
        try:
            return self.runner(command, timeout=self.timeout, **kwargs)
        except ToolError as exc:
            raise self.ERROR(str(exc)) from exc
