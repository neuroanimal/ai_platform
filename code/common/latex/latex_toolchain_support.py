"""
Shared implementation of the LaTeX-family adapters.

``render(content)`` returns a complete, compilable source file for the
adapter's language (a ``standalone`` LaTeX document for TikZ/PGF/PGFPlots/
CircuiTikZ, an Asymptote file, a MetaPost file). ``compile(source,
output_path)`` runs the real toolchain in a temporary directory and copies
the result to ``output_path``; the output format follows its extension.

Toolchains (resolved on PATH, first match wins):

    LaTeX      latexmk (-pdf / -lualatex), else pdflatex / lualatex / xelatex
    Asymptote  asy  (-f pdf|svg|png)
    MetaPost   mpost (outputformat "svg" or "eps"; .pdf via mptopdf if present)

``compile`` accepts a body (anything ``render`` accepts) or a full document:
a source that already contains ``\\documentclass`` / ``beginfig`` / is meant
as Asymptote is compiled as-is.

Configuration (``initialize``):

    engine      "pdflatex" (default), "lualatex" or "xelatex"
    packages    extra LaTeX packages for the preamble
    preamble    extra raw preamble lines
    timeout     seconds per toolchain run, default 120
    runner      replacement for ``run_tool`` (tests)
"""

import os
import shutil
import tempfile
from typing import Any, Callable, Dict, List, Optional

from ai_platform.common.latex.base import LaTeXAdapter
from ai_platform.common.util.cli_runner import ToolError, find_tool, run_tool

ENGINES = ("pdflatex", "lualatex", "xelatex")


class LaTeXError(Exception):
    """LaTeX adapter misuse or toolchain failure."""


class LaTeXDocumentAdapter(LaTeXAdapter):
    """Base for adapters that produce a standalone LaTeX document."""

    #: LaTeX packages the adapter's environment needs.
    PACKAGES: List[str] = []
    #: (begin, end) wrapper for the body; None = body used as-is inside document.
    ENVIRONMENT: Optional[tuple] = None
    #: Extra preamble lines (e.g. \pgfplotsset{compat=...}).
    PREAMBLE: List[str] = []
    #: Output extensions compile() can produce.
    FORMATS = (".pdf",)

    def __init__(self):
        self.initialized = False
        self.engine = "pdflatex"
        self.packages: List[str] = []
        self.preamble: List[str] = []
        self.timeout = 120.0
        self.runner: Callable = run_tool
        self.last_log = ""

    def initialize(self, config: Dict[str, Any]) -> None:
        """Read engine, preamble and runner."""
        config = dict(config or {})
        self.engine = config.get("engine", "pdflatex")
        if self.engine not in ENGINES:
            raise LaTeXError(f"engine must be one of {ENGINES}")
        self.packages = list(config.get("packages", []))
        self.preamble = list(config.get("preamble", []))
        self.timeout = float(config.get("timeout", 120))
        self.runner = config.get("runner", run_tool)
        self.initialized = True

    def render(self, content: str, **kwargs) -> str:
        """Wrap ``content`` into a complete standalone document.

        ``kwargs['options']`` is inserted as the environment's optional
        argument, e.g. ``options="scale=2"`` -> ``\\begin{tikzpicture}[scale=2]``.
        """
        self._require()
        body = content
        if self.ENVIRONMENT:
            begin, end = self.ENVIRONMENT
            options = f"[{kwargs['options']}]" if kwargs.get("options") else ""
            body = f"{begin}{options}\n{content}\n{end}"
        lines = ["\\documentclass[border=2pt]{standalone}"]
        lines += [f"\\usepackage{{{p}}}" for p in [*self.PACKAGES, *self.packages]]
        lines += [*self.PREAMBLE, *self.preamble]
        lines += ["\\begin{document}", body, "\\end{document}", ""]
        return "\n".join(lines)

    def compile(self, source: str, output_path: str) -> None:
        """Compile ``source`` (body or full document) to ``output_path``."""
        self._require()
        extension = os.path.splitext(output_path)[1].lower()
        if extension not in self.FORMATS:
            raise LaTeXError(f"{type(self).__name__} can write {self.FORMATS}, not {extension!r}")
        document = source if "\\documentclass" in source else self.render(source)
        with tempfile.TemporaryDirectory(prefix="ai_platform_tex_") as work:
            with open(os.path.join(work, "doc.tex"), "w", encoding="utf-8") as handle:
                handle.write(document)
            self._run(self._latex_command(), work)
            produced = os.path.join(work, "doc.pdf")
            if not os.path.exists(produced):
                raise LaTeXError(f"no PDF produced; log tail: {self.last_log[-1500:]}")
            self._copy(produced, output_path)

    def shutdown(self) -> None:
        """Nothing to release."""
        self.initialized = False

    # -- helpers ------------------------------------------------------------

    def _latex_command(self) -> List[str]:
        try:
            latexmk = find_tool(["latexmk"])
            mode = {"pdflatex": "-pdf", "lualatex": "-lualatex", "xelatex": "-xelatex"}[self.engine]
            return [latexmk, mode, "-interaction=nonstopmode", "-halt-on-error", "doc.tex"]
        except ToolError:
            try:
                engine = find_tool([self.engine], hint="install a TeX distribution, e.g. TeX Live")
            except ToolError as exc:
                raise LaTeXError(str(exc)) from exc
            return [engine, "-interaction=nonstopmode", "-halt-on-error", "doc.tex"]

    def _run(self, command: List[str], cwd: str) -> None:
        try:
            result = self.runner(command, timeout=self.timeout, cwd=cwd)
        except ToolError as exc:
            raise LaTeXError(str(exc)) from exc
        self.last_log = getattr(result, "stdout", "") or ""

    @staticmethod
    def _copy(produced: str, output_path: str) -> None:
        folder = os.path.dirname(os.path.abspath(output_path))
        os.makedirs(folder, exist_ok=True)
        shutil.copyfile(produced, output_path)

    def _require(self) -> None:
        if not self.initialized:
            raise LaTeXError(f"{type(self).__name__} is not initialized")
