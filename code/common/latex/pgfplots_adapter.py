"""PGFPlots adapter.

Body is the content of an ``axis`` environment (``\\addplot ...;``) inside a
``tikzpicture``. ``options`` become the axis options.

Uses the shared toolchain base (``latex_toolchain_support.py``): ``render``
returns a complete standalone document, ``compile`` runs latexmk/pdflatex
for real. Previously a stub that compiled nothing; the class name and the
LaTeXAdapter methods are unchanged.
"""

from ai_platform.common.latex.latex_toolchain_support import LaTeXDocumentAdapter


class PGFPlotsAdapter(LaTeXDocumentAdapter):
    """PGFPlots axes."""

    PACKAGES = ["pgfplots"]
    ENVIRONMENT = ("\\begin{tikzpicture}\\begin{axis}", "\\end{axis}\\end{tikzpicture}")
    PREAMBLE = ["\\pgfplotsset{compat=1.18}"]
