"""MetaPost adapter.

``render(content, format="svg")`` returns a complete MetaPost file with one
figure (``beginfig(1) ... endfig; end``) and the output format set;
``compile`` runs ``mpost`` for real. Output extensions: .svg (MetaPost's
SVG backend) and .eps (encapsulated PostScript, ``.mps``).

Previously a stub that compiled nothing; the class name and the
LaTeXAdapter methods are unchanged.
"""

import os
import tempfile

from ai_platform.common.latex.latex_toolchain_support import LaTeXDocumentAdapter, LaTeXError
from ai_platform.common.util.cli_runner import ToolError, find_tool

_FORMAT = {".svg": "svg", ".eps": "eps"}


class MetaPostAdapter(LaTeXDocumentAdapter):
    """MetaPost figures."""

    FORMATS = tuple(_FORMAT)

    def render(self, content: str, **kwargs) -> str:
        """Complete MetaPost program around one figure."""
        self._require()
        fmt = kwargs.get("format", "svg")
        return "\n".join([
            "prologues := 3;",
            f'outputformat := "{fmt}";',
            'outputtemplate := "%j-%c.%o";',
            *self.preamble,
            "beginfig(1);", content, "endfig;", "end.", ""])

    def compile(self, source: str, output_path: str) -> None:
        """Run mpost and copy figure 1."""
        self._require()
        extension = os.path.splitext(output_path)[1].lower()
        if extension not in _FORMAT:
            raise LaTeXError(f"MetaPostAdapter can write {self.FORMATS}, not {extension!r}")
        program = source if "beginfig" in source else self.render(source, format=_FORMAT[extension])
        try:
            mpost = find_tool(["mpost"], hint="install a TeX distribution with MetaPost")
        except ToolError as exc:
            raise LaTeXError(str(exc)) from exc
        with tempfile.TemporaryDirectory(prefix="ai_platform_mp_") as work:
            with open(os.path.join(work, "doc.mp"), "w", encoding="utf-8") as handle:
                handle.write(program)
            self._run([mpost, "-interaction=nonstopmode", "doc.mp"], work)
            produced = os.path.join(work, f"doc-1.{_FORMAT[extension]}")
            if not os.path.exists(produced):
                raise LaTeXError(f"mpost produced no figure; log: {self.last_log[-1500:]}")
            self._copy(produced, output_path)
