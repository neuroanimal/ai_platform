"""SVG.js adapter.

Generates JavaScript for SVG.js 3.x (https://svgjs.dev); see ``svg_javascript_support.py``
for what is and is not done in Python. The generated code is checked for
JavaScript syntax in the unit tests (``node --check``) but has not been run
in a browser here. Previously a stub returning a fabricated string; the
class name and the SVGAdapter methods are unchanged.
"""

# One branch per SVG shape type is clearer than a dispatch table here.
# pylint: disable=too-many-return-statements

from typing import Any, Dict

from ai_platform.common.svg.svg_javascript_support import JavaScriptSVGAdapter, js


class SVGJSAdapter(JavaScriptSVGAdapter):
    """SVG.js drawing code."""

    LIBRARY = "SVG.js"
    LIBRARY_URL = "https://cdn.jsdelivr.net/npm/@svgdotjs/svg.js@3.2/dist/svg.min.js"

    def canvas(self, width: Any, height: Any) -> str:
        target = js("#" + self.container_id)
        return f"var paper = SVG().addTo({target}).size({js(width)}, {js(height)})"

    def shape(self, kind: str, element: Dict[str, Any], attrs: Dict[str, Any]) -> str:
        g = attrs.get
        if kind == "rect":
            call = (f"paper.rect({js(g('width', 0))}, {js(g('height', 0))})"
                    f".move({js(g('x', 0))}, {js(g('y', 0))})")
            return self.with_attrs(call, attrs, ["x", "y", "width", "height"])
        if kind == "circle":
            call = f"paper.circle(2 * {js(g('r', 0))}).center({js(g('cx', 0))}, {js(g('cy', 0))})"
            return self.with_attrs(call, attrs, ["cx", "cy", "r"])
        if kind == "ellipse":
            call = (f"paper.ellipse(2 * {js(g('rx', 0))}, 2 * {js(g('ry', 0))})"
                    f".center({js(g('cx', 0))}, {js(g('cy', 0))})")
            return self.with_attrs(call, attrs, ["cx", "cy", "rx", "ry"])
        if kind == "line":
            args = ", ".join(js(g(n, 0)) for n in ("x1", "y1", "x2", "y2"))
            return self.with_attrs(f"paper.line({args})", attrs, ["x1", "y1", "x2", "y2"])
        if kind in ("polyline", "polygon"):
            return self.with_attrs(f"paper.{kind}({js(g('points', ''))})", attrs, ["points"])
        if kind == "text":
            call = f"paper.text({js(str(element.get('text', '')))})"
            return self.with_attrs(call, attrs, [])
        return self.with_attrs(f"paper.path({js(g('d', ''))})", attrs, ["d"])
