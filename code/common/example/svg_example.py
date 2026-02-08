"""Example usage of SVG adapters."""

from code.common.svg.svg_registry import get_registry
from code.common.svg.svgwrite_adapter import SvgwriteAdapter
from code.common.svg.snapsvg_adapter import SnapSVGAdapter
from code.common.svg.svgjs_adapter import SVGJSAdapter
from code.common.svg.raphael_adapter import RaphaelAdapter
from code.common.svg.inkscape_adapter import InkscapeAdapter

def main():
    registry = get_registry()

    tools = {
        "svgwrite": SvgwriteAdapter,
        "snapsvg": SnapSVGAdapter,
        "svgjs": SVGJSAdapter,
        "raphael": RaphaelAdapter,
        "inkscape": InkscapeAdapter,
    }

    for name, adapter_class in tools.items():
        registry.register(name, adapter_class)

    print(f"Registered {len(tools)} SVG tools: {registry.list()}\n")

    for name in tools.keys():
        adapter = registry.get(name)
        adapter.initialize({})
        result = adapter.create('<circle cx="50" cy="50" r="40"/>')
        print(f"{name}: {result[:60]}...")
        adapter.shutdown()

if __name__ == "__main__":
    main()
