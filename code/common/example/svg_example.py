"""Example usage of SVG adapters.

Registers every adapter and exercises each one with a small, real operation -
output goes to a temporary directory. Nothing is fabricated: an adapter whose
tool, server or package is not available here is reported as skipped with the
reason.

    python -m ai_platform.common.example.svg_example
"""

# Examples follow the same register-and-try pattern on purpose.
# pylint: disable=duplicate-code

import os
import tempfile

from ai_platform.common.svg.inkscape_adapter import InkscapeAdapter
from ai_platform.common.svg.native_svg_adapter import NativeSVGAdapter
from ai_platform.common.svg.raphael_adapter import RaphaelAdapter
from ai_platform.common.svg.snapsvg_adapter import SnapSVGAdapter
from ai_platform.common.svg.svg_registry import get_registry
from ai_platform.common.svg.svg_support import SVGError
from ai_platform.common.svg.svgjs_adapter import SVGJSAdapter
from ai_platform.common.svg.svgwrite_adapter import SvgwriteAdapter


def main():
    """Register all adapters and exercise the usable ones."""
    registry = get_registry()

    tools = {
        "native": NativeSVGAdapter,
        "svgwrite": SvgwriteAdapter,
        "snapsvg": SnapSVGAdapter,
        "svgjs": SVGJSAdapter,
        "raphael": RaphaelAdapter,
        "inkscape": InkscapeAdapter,
    }

    for name, adapter_class in tools.items():
        registry.register(name, adapter_class)

    print(f"Registered {len(tools)}: {registry.list()}\n")

    elements = [{"type": "rect", "x": 10, "y": 10, "width": 80, "height": 40, "fill": "#36c"},
                {"type": "text", "x": 12, "y": 70, "text": "AI Platform"}]
    suffix = {"svgwrite": ".svg", "native": ".svg", "inkscape": ".png"}
    with tempfile.TemporaryDirectory() as tmp:
        for name in tools:
            adapter = registry.get(name)
            try:
                adapter.initialize({})
                content = adapter.create(elements, width=120, height=90)
                target = os.path.join(tmp, name + suffix.get(name, ".html"))
                adapter.save(content, target)
                print(f"{name:9} OK      {os.path.basename(target)} "
                      f"({os.path.getsize(target)} bytes)")
            except SVGError as exc:
                print(f"{name:9} skipped {type(exc).__name__}: {str(exc)[:80]}")
            finally:
                adapter.shutdown()


if __name__ == "__main__":
    main()
