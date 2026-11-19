"""CircuiTikZ adapter.

Body is circuit code (``\\draw (0,0) to[R=$R_1$] (2,0);``) inside ``circuitikz``.

Uses the shared toolchain base (``latex_toolchain_support.py``): ``render``
returns a complete standalone document, ``compile`` runs latexmk/pdflatex
for real. Previously a stub that compiled nothing; the class name and the
LaTeXAdapter methods are unchanged.
"""

from ai_platform.common.latex.latex_toolchain_support import LaTeXDocumentAdapter


class CircuiTikZAdapter(LaTeXDocumentAdapter):
    """CircuiTikZ circuits."""

    PACKAGES = ["circuitikz"]
    ENVIRONMENT = ("\\begin{circuitikz}", "\\end{circuitikz}")
