"""Asymptote adapter (https://asymptote.sourceforge.io).

``render(content, size="6cm")`` returns an Asymptote program (adds a
``size(...)`` line unless the content sets one). ``compile`` runs
``asy -f <format> -o doc doc.asy`` for real; the format follows the output
extension (.pdf, .svg, .png, .eps). PDF/PNG output needs a LaTeX
installation, which Asymptote uses for labels.

Previously a stub that compiled nothing; the class name and the
LaTeXAdapter methods are unchanged.
"""

import os
import tempfile
from typing import List

from ai_platform.common.latex.latex_toolchain_support import LaTeXDocumentAdapter, LaTeXError
from ai_platform.common.util.cli_runner import ToolError, find_tool


class AsymptoteAdapter(LaTeXDocumentAdapter):
    """Asymptote vector graphics."""

    FORMATS = (".pdf", ".svg", ".png", ".eps")

    def render(self, content: str, **kwargs) -> str:
        """Asymptote source with a default picture size."""
        self._require()
        lines: List[str] = []
        if "size(" not in content:
            lines.append(f"size({kwargs.get('size', '6cm')});")
        lines += [*self.preamble, content, ""]
        return "\n".join(lines)

    def compile(self, source: str, output_path: str) -> None:
        """Run asy and copy the produced file."""
        self._require()
        extension = os.path.splitext(output_path)[1].lower()
        if extension not in self.FORMATS:
            raise LaTeXError(f"AsymptoteAdapter can write {self.FORMATS}, not {extension!r}")
        program = source if "size(" in source else self.render(source)
        try:
            asy = find_tool(["asy"], hint="install Asymptote")
        except ToolError as exc:
            raise LaTeXError(str(exc)) from exc
        with tempfile.TemporaryDirectory(prefix="ai_platform_asy_") as work:
            with open(os.path.join(work, "doc.asy"), "w", encoding="utf-8") as handle:
                handle.write(program)
            self._run([asy, "-f", extension[1:], "-o", "doc", "doc.asy"], work)
            produced = os.path.join(work, "doc" + extension)
            if not os.path.exists(produced):
                raise LaTeXError(f"asy produced no {extension}; output: {self.last_log[-1500:]}")
            self._copy(produced, output_path)
