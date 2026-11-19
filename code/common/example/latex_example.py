"""Example usage of LaTeX-family adapters.

Registers every adapter and exercises each one with a small, real
operation - render always, compile when the toolchain is
installed. Nothing is fabricated: an adapter whose tool, server or
package is not available here is reported as skipped with the reason.

    python -m ai_platform.common.example.latex_example
"""

# Examples follow the same register-and-try pattern on purpose.
# pylint: disable=duplicate-code

import os
import tempfile

from ai_platform.common.latex.asymptote_adapter import AsymptoteAdapter
from ai_platform.common.latex.circuitikz_adapter import CircuiTikZAdapter
from ai_platform.common.latex.latex_registry import get_registry
from ai_platform.common.latex.latex_toolchain_support import LaTeXError
from ai_platform.common.latex.metapost_adapter import MetaPostAdapter
from ai_platform.common.latex.pgf_adapter import PGFAdapter
from ai_platform.common.latex.pgfplots_adapter import PGFPlotsAdapter
from ai_platform.common.latex.tikz_adapter import TikZAdapter


def main():
    """Register all adapters and exercise the usable ones."""
    registry = get_registry()

    tools = {
        "tikz": TikZAdapter,
        "pgf": PGFAdapter,
        "pgfplots": PGFPlotsAdapter,
        "asymptote": AsymptoteAdapter,
        "metapost": MetaPostAdapter,
        "circuitikz": CircuiTikZAdapter,
    }

    for name, adapter_class in tools.items():
        registry.register(name, adapter_class)

    print(f"Registered {len(tools)}: {registry.list()}\n")

    bodies = {"asymptote": "draw((0,0)--(1,1));", "metapost": "draw (0,0)--(20,20);",
              "pgf": "\\pgfpathmoveto{\\pgfpointorigin}\\pgfpathlineto{\\pgfpoint{1cm}{1cm}}"
                     "\\pgfusepath{stroke}",
              "pgfplots": "\\addplot {x^2};", "circuitikz": "\\draw (0,0) to[R] (2,0);"}
    with tempfile.TemporaryDirectory() as tmp:
        for name in tools:
            adapter = registry.get(name)
            adapter.initialize({})
            body = bodies.get(name, "\\draw (0,0) -- (1,1);")
            source = adapter.render(body)
            target = os.path.join(tmp, f"{name}{adapter.FORMATS[0]}")
            try:
                adapter.compile(source, target)
                print(f"{name:10} OK      compiled {os.path.getsize(target)} bytes")
            except LaTeXError as exc:
                print(f"{name:10} render  {len(source)} chars; compile skipped: {str(exc)[:60]}")
            finally:
                adapter.shutdown()


if __name__ == "__main__":
    main()
