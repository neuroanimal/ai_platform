"""PGF (basic layer) adapter.

Body is PGF basic-layer code drawn inside ``pgfpicture`` (``\\pgfpathmoveto``,
``\\pgfusepath`` ...).

Uses the shared toolchain base (``latex_toolchain_support.py``): ``render``
returns a complete standalone document, ``compile`` runs latexmk/pdflatex
for real. Previously a stub that compiled nothing; the class name and the
LaTeXAdapter methods are unchanged.
"""

from ai_platform.common.latex.latex_toolchain_support import LaTeXDocumentAdapter


class PGFAdapter(LaTeXDocumentAdapter):
    """PGF basic-layer pictures."""

    PACKAGES = ["pgf"]
    ENVIRONMENT = ("\\begin{pgfpicture}", "\\end{pgfpicture}")
