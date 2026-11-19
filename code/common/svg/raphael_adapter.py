"""Raphael adapter.

Generates JavaScript for Raphael 2.x
(https://dmitrybaranovskiy.github.io/raphael/); see ``svg_javascript_support.py``
for what is and is not done in Python. The generated code is checked for
JavaScript syntax in the unit tests (``node --check``) but has not been run
in a browser here. Previously a stub returning a fabricated string; the
class name and the SVGAdapter methods are unchanged.
"""

# One branch per SVG shape type is clearer than a dispatch table here.
# pylint: disable=too-many-return-statements

from typing import Any, Dict

from ai_platform.common.svg.svg_javascript_support import JavaScriptSVGAdapter, js


class RaphaelAdapter(JavaScriptSVGAdapter):
    """Raphael drawing code."""

    LIBRARY = "Raphael"
    LIBRARY_URL = "https://cdnjs.cloudflare.com/ajax/libs/raphael/2.3.0/raphael.min.js"

    def canvas(self, width: Any, height: Any) -> str:
        return f"var paper = Raphael({js(self.container_id)}, {js(width)}, {js(height)})"

    def shape(self, kind: str, element: Dict[str, Any], attrs: Dict[str, Any]) -> str:
        g = attrs.get
        if kind == "rect":
            args = ", ".join(js(g(n, 0)) for n in ("x", "y", "width", "height"))
            call = f"paper.rect({args})"
            return self.with_attrs(call, attrs, ["x", "y", "width", "height"])
        if kind == "circle":
            call = f"paper.circle({js(g('cx', 0))}, {js(g('cy', 0))}, {js(g('r', 0))})"
            return self.with_attrs(call, attrs, ["cx", "cy", "r"])
        if kind == "ellipse":
            call = (f"paper.ellipse({js(g('cx', 0))}, {js(g('cy', 0))}, "
                    f"{js(g('rx', 0))}, {js(g('ry', 0))})")
            return self.with_attrs(call, attrs, ["cx", "cy", "rx", "ry"])
        if kind == "text":
            label = js(str(element.get("text", "")))
            call = f"paper.text({js(g('x', 0))}, {js(g('y', 0))}, {label})"
            return self.with_attrs(call, attrs, ["x", "y"])
        # Raphael has no line/polyline/polygon primitives: draw them as paths.
        if kind == "line":
            d = f"M{g('x1', 0)},{g('y1', 0)}L{g('x2', 0)},{g('y2', 0)}"
            return self.with_attrs(f"paper.path({js(d)})", attrs, ["x1", "y1", "x2", "y2"])
        if kind in ("polyline", "polygon"):
            pts = str(g("points", "")).split()
            d = "M" + "L".join(pts) + ("Z" if kind == "polygon" else "")
            return self.with_attrs(f"paper.path({js(d)})", attrs, ["points"])
        return self.with_attrs(f"paper.path({js(g('d', ''))})", attrs, ["d"])
