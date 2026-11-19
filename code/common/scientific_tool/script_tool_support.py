"""
Shared implementation of the scientific tool adapters.

``execute(script)`` runs the script in the tool's own interpreter, as a
separate process, and returns its standard output (stripped). The complete
result (stdout, stderr, command) is kept in ``last_result``.

Security: these adapters execute arbitrary code by design - pass only
scripts you would run yourself. The script is handed over as one argument
(no shell), so it cannot inject shell syntax, but it can do anything the
tool's language can.

Configuration (``connect``): ``timeout`` (default 300), ``executable``,
``cwd`` (working directory for the run), ``runner`` (tests).
"""

from typing import Any, Dict, List, Optional

from ai_platform.common.scientific_tool.base import ScientificToolAdapter
from ai_platform.common.util.cli_runner import CLIToolMixin


class ScientificToolError(Exception):
    """Missing tool or failed script."""


class ScriptToolAdapter(CLIToolMixin, ScientificToolAdapter):
    """Runs one script per call in an external interpreter."""

    DEFAULT_TIMEOUT = 300.0
    ERROR = ScientificToolError

    def __init__(self):
        self.connected = False
        self.cwd: Optional[str] = None
        self.last_result = None

    def connect(self, config: Dict[str, Any]) -> None:
        """Locate the interpreter."""
        self._configure_cli(config)
        self.cwd = (config or {}).get("cwd")
        self.connected = True

    def execute(self, script: str, **kwargs) -> Any:
        """Run ``script``; return its stdout."""
        if not self.connected:
            raise ScientificToolError(f"{type(self).__name__} is not connected")
        if not str(script).strip():
            raise ScientificToolError("script is empty")
        self.last_result = self._run_cli(self.command(str(script)), cwd=kwargs.get("cwd", self.cwd))
        return self.last_result.stdout.strip()

    def disconnect(self) -> None:
        """Nothing to release (each call is its own process)."""
        self.connected = False

    def command(self, script: str) -> List[str]:
        """Argument list running ``script``."""
        raise NotImplementedError
