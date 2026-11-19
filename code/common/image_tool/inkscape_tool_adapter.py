"""Inkscape image tool adapter (Inkscape 1.x command line).

Converts/rasterizes vector input (SVG, and what Inkscape imports: PDF, EPS,
AI) for real::

    inkscape in.svg --export-filename=out.png --export-width=800 --export-dpi=150

Operations (see ``image_operations.py`` for the shared keys):

    format      png (default), pdf, eps, ps, svg
    width, height   PNG pixel size (one keeps the aspect ratio)
    dpi         PNG resolution
    area        "page" (default) or "drawing" (bounding box of the content)
    background  PNG background colour, e.g. "#ffffff"
    output      output path

Configuration: ``timeout`` (default 120), ``executable``, ``runner`` (tests).
Previously a stub that returned a fake path; the class name and the
ImageToolAdapter methods are unchanged.
"""

# The CLI adapters share their connect/process skeleton by design.
# pylint: disable=duplicate-code

from typing import Any, Dict, List

from ai_platform.common.image_tool.base import ImageToolAdapter
from ai_platform.common.image_tool.image_operations import (
    ImageToolError,
    check_operations,
    output_path,
    require_input,
)
from ai_platform.common.util.cli_runner import CLIToolMixin

SUPPORTED = ("width", "height", "dpi", "area", "background")
FORMATS = ("png", "pdf", "eps", "ps", "svg")


class InkscapeToolAdapter(CLIToolMixin, ImageToolAdapter):
    """Vector-to-raster/vector conversion with Inkscape."""

    TOOLS = ["inkscape"]
    HINT = "install Inkscape 1.x"
    DEFAULT_TIMEOUT = 120.0
    ERROR = ImageToolError

    def __init__(self):
        self.connected = False

    def connect(self, config: Dict[str, Any]) -> None:
        """Locate inkscape."""
        self._configure_cli(config)
        self.connected = True

    def process(self, input_path: str, operations: Dict[str, Any]) -> str:
        """Export ``input_path``; return the output path."""
        if not self.connected:
            raise ImageToolError("InkscapeToolAdapter is not connected")
        require_input(input_path)
        check_operations(operations, SUPPORTED)
        target, ext = output_path(input_path, operations, default_ext="png")
        if ext not in FORMATS:
            raise ImageToolError(f"Inkscape exports {FORMATS}, not {ext!r}")
        command: List[str] = [self.executable, input_path, f"--export-filename={target}"]
        if ext == "svg":
            command.append("--export-plain-svg")
        if operations.get("area", "page") == "drawing":
            command.append("--export-area-drawing")
        for key, flag in (("width", "--export-width"), ("height", "--export-height"),
                          ("dpi", "--export-dpi")):
            if key in operations:
                command.append(f"{flag}={int(operations[key])}")
        if "background" in operations:
            command.append(f"--export-background={operations['background']}")
        self._run_cli(command)
        return target

    def disconnect(self) -> None:
        """Nothing to release."""
        self.connected = False
