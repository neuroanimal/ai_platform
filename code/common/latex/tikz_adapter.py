"""TikZ adapter.

Body is TikZ code drawn inside ``tikzpicture``.

Uses the shared toolchain base (``latex_toolchain_support.py``): ``render``
returns a complete standalone document, ``compile`` runs latexmk/pdflatex
for real. Previously a stub that compiled nothing; the class name and the
LaTeXAdapter methods are unchanged.
"""

from ai_platform.common.latex.latex_toolchain_support import LaTeXDocumentAdapter


class TikZAdapter(LaTeXDocumentAdapter):
    """TikZ pictures."""

    PACKAGES = ["tikz"]
    ENVIRONMENT = ("\\begin{tikzpicture}", "\\end{tikzpicture}")
