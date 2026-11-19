"""Snap.svg adapter.

Generates JavaScript for Snap.svg 0.5 (http://snapsvg.io); see ``svg_javascript_support.py``
for what is and is not done in Python. The generated code is checked for
JavaScript syntax in the unit tests (``node --check``) but has not been run
in a browser here. Previously a stub returning a fabricated string; the
class name and the SVGAdapter methods are unchanged.
"""

# One branch per SVG shape type is clearer than a dispatch table here.
# pylint: disable=too-many-return-statements

from typing import Any, Dict

from ai_platform.common.svg.svg_javascript_support import JavaScriptSVGAdapter, js


class SnapSVGAdapter(JavaScriptSVGAdapter):
    """Snap.svg drawing code."""

    LIBRARY = "Snap.svg"
    LIBRARY_URL = "https://cdnjs.cloudflare.com/ajax/libs/snap.svg/0.5.1/snap.svg-min.js"

    def canvas(self, width: Any, height: Any) -> str:
        return (f"var paper = Snap({js(width)}, {js(height)}); "
                f"document.getElementById({js(self.container_id)}).appendChild(paper.node)")

    def shape(self, kind: str, element: Dict[str, Any], attrs: Dict[str, Any]) -> str:
        g = attrs.get
        positional = {
            "rect": ["x", "y", "width", "height"],
            "circle": ["cx", "cy", "r"],
            "ellipse": ["cx", "cy", "rx", "ry"],
            "line": ["x1", "y1", "x2", "y2"],
        }
        if kind in positional:
            args = ", ".join(js(g(name, 0)) for name in positional[kind])
            return self.with_attrs(f"paper.{kind}({args})", attrs, positional[kind])
        if kind == "text":
            label = js(str(element.get("text", "")))
            call = f"paper.text({js(g('x', 0))}, {js(g('y', 0))}, {label})"
            return self.with_attrs(call, attrs, ["x", "y"])
        if kind in ("polyline", "polygon"):
            numbers = [float(n) for p in str(g("points", "")).split() for n in p.split(",")]
            return self.with_attrs(f"paper.{kind}({js(numbers)})", attrs, ["points"])
        return self.with_attrs(f"paper.path({js(g('d', ''))})", attrs, ["d"])
