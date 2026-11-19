"""Dia diagram adapter (Dia command line export).

Exports a Dia diagram (``.dia``) for real::

    dia --nosplash --export=out.png --filter=png [--size=800x] in.dia

Operations: ``format`` (png default, svg, eps, pdf - as the installed Dia
build supports), ``width`` / ``height`` (raster size; Dia keeps the aspect
ratio when one is given), ``output``.

Configuration: ``timeout`` (default 120), ``executable``, ``runner`` (tests).
Not verified against an installed Dia here. Previously a stub that
returned a fake path; the class name and the ImageToolAdapter methods are
unchanged.
"""

# The CLI adapters share their connect/process skeleton by design.
# pylint: disable=duplicate-code

from typing import Any, Dict

from ai_platform.common.image_tool.base import ImageToolAdapter
from ai_platform.common.image_tool.image_operations import (
    ImageToolError,
    check_operations,
    output_path,
    require_input,
)
from ai_platform.common.util.cli_runner import CLIToolMixin

SUPPORTED = ("width", "height")
# Dia's export filter names for the output extension.
FILTERS = {"png": "png", "svg": "svg", "eps": "eps", "pdf": "pdf", "jpg": "jpg"}


class DiaAdapter(CLIToolMixin, ImageToolAdapter):
    """Diagram export through the Dia CLI."""

    TOOLS = ["dia"]
    HINT = "install Dia"
    DEFAULT_TIMEOUT = 120.0
    ERROR = ImageToolError

    def __init__(self):
        self.connected = False

    def connect(self, config: Dict[str, Any]) -> None:
        """Locate dia."""
        self._configure_cli(config)
        self.connected = True

    def process(self, input_path: str, operations: Dict[str, Any]) -> str:
        """Export the diagram; return the output path."""
        if not self.connected:
            raise ImageToolError("DiaAdapter is not connected")
        require_input(input_path)
        check_operations(operations, SUPPORTED)
        target, ext = output_path(input_path, operations, default_ext="png")
        if ext not in FILTERS:
            raise ImageToolError(f"Dia exports {sorted(FILTERS)}, not {ext!r}")
        command = [self.executable, "--nosplash", f"--export={target}", f"--filter={FILTERS[ext]}"]
        if "width" in operations or "height" in operations:
            width = operations.get("width", "")
            height = operations.get("height", "")
            command.append(f"--size={width}x{height}")
        command.append(input_path)
        self._run_cli(command)
        return target

    def disconnect(self) -> None:
        """Nothing to release."""
        self.connected = False
