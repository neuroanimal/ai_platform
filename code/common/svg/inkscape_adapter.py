"""Inkscape SVG adapter.

``create`` builds SVG markup (stdlib writer, see ``svg_support.py``).
``save`` writes it; when ``output_path`` is not ``.svg`` the drawing is
exported with the Inkscape 1.x command line for real::

    inkscape drawing.svg --export-filename=<output> [--export-dpi=<dpi>]

which supports .png, .pdf, .eps and .ps; a .svg output is written directly.

Configuration: ``dpi`` (PNG export, default 96), ``timeout`` (default 120),
``runner`` (tests). Previously a stub that saved nothing; the class name
and the SVGAdapter methods are unchanged.
"""

import os
import tempfile
from typing import Any, Callable, Dict

from ai_platform.common.svg.base import SVGAdapter
from ai_platform.common.svg.svg_support import SVGError, build_svg, write_text
from ai_platform.common.util.cli_runner import ToolError, find_tool, run_tool

EXPORT_FORMATS = (".png", ".pdf", ".eps", ".ps")


class InkscapeAdapter(SVGAdapter):
    """SVG creation plus export through the Inkscape CLI."""

    def __init__(self):
        self.initialized = False
        self.dpi = 96
        self.timeout = 120.0
        self.runner: Callable = run_tool

    def initialize(self, config: Dict[str, Any]) -> None:
        """Read export settings."""
        config = dict(config or {})
        self.dpi = int(config.get("dpi", 96))
        self.timeout = float(config.get("timeout", 120))
        self.runner = config.get("runner", run_tool)
        self.initialized = True

    def create(self, elements: Any, **kwargs) -> str:
        """SVG markup for ``elements``."""
        self._require()
        return build_svg(elements, **kwargs)

    def save(self, svg_content: str, output_path: str) -> None:
        """Write SVG, or export it to the format of ``output_path``."""
        self._require()
        extension = os.path.splitext(output_path)[1].lower()
        if extension == ".svg":
            write_text(svg_content, output_path)
            return
        if extension not in EXPORT_FORMATS:
            raise SVGError(f"Inkscape export supports .svg and {EXPORT_FORMATS}, not {extension!r}")
        try:
            inkscape = find_tool(["inkscape"], hint="install Inkscape 1.x")
        except ToolError as exc:
            raise SVGError(str(exc)) from exc
        with tempfile.TemporaryDirectory(prefix="ai_platform_inkscape_") as work:
            source = os.path.join(work, "drawing.svg")
            write_text(svg_content, source)
            command = [inkscape, source, f"--export-filename={os.path.abspath(output_path)}"]
            if extension == ".png":
                command.append(f"--export-dpi={self.dpi}")
            try:
                self.runner(command, timeout=self.timeout, cwd=work)
            except ToolError as exc:
                raise SVGError(str(exc)) from exc

    def shutdown(self) -> None:
        """Nothing to release."""
        self.initialized = False

    def _require(self) -> None:
        if not self.initialized:
            raise SVGError("InkscapeAdapter is not initialized")
