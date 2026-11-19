"""
Shared element model of the SVG adapters, and a stdlib SVG writer.

Elements passed to ``create()`` are dicts with a ``type`` and that shape's
attributes, in SVG's own attribute names::

    {"type": "rect", "x": 10, "y": 10, "width": 80, "height": 40, "fill": "#36c"}
    {"type": "circle", "cx": 50, "cy": 50, "r": 20, "stroke": "black"}
    {"type": "ellipse", "cx": 50, "cy": 50, "rx": 30, "ry": 10}
    {"type": "line", "x1": 0, "y1": 0, "x2": 100, "y2": 100, "stroke": "red"}
    {"type": "polyline" | "polygon", "points": [[0, 0], [10, 20], [20, 0]]}
    {"type": "path", "d": "M 10 10 L 90 90"}
    {"type": "text", "x": 10, "y": 20, "text": "Etykieta", "font-size": 12}

``create(elements, width=..., height=...)`` returns the drawing in the
adapter's output form (SVG markup or JavaScript for the browser libraries).
Unknown element types raise ``SVGError`` rather than being dropped.
"""

import xml.etree.ElementTree as ET
from typing import Any, Dict, Iterable, List, Sequence

SVG_NS = "http://www.w3.org/2000/svg"
SHAPES = ("rect", "circle", "ellipse", "line", "polyline", "polygon", "path", "text")


class SVGError(Exception):
    """Invalid element description or failed export."""


def points_text(points: Sequence[Sequence[float]]) -> str:
    """[[x, y], ...] -> "x,y x,y" (strings are passed through)."""
    if isinstance(points, str):
        return points
    return " ".join(f"{x},{y}" for x, y in points)


def check_elements(elements: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate element dicts and return them as a list."""
    checked = []
    for number, element in enumerate(elements or []):
        if not isinstance(element, dict) or element.get("type") not in SHAPES:
            raise SVGError(f"element {number}: 'type' must be one of {SHAPES}, got {element!r}")
        checked.append(element)
    return checked


def attributes(element: Dict[str, Any]) -> Dict[str, str]:
    """SVG attributes of an element (without type/text), as strings."""
    attrs = {}
    for key, value in element.items():
        if key in ("type", "text"):
            continue
        attrs[key] = points_text(value) if key == "points" else str(value)
    return attrs


def build_svg(elements: Iterable[Dict[str, Any]], width: Any = 200, height: Any = 200,
              background: str = "") -> str:
    """Serialize elements to SVG markup with the standard library.

    ElementTree escapes text and attribute values, so labels such as
    ``a < b & c`` produce valid XML.
    """
    ET.register_namespace("", SVG_NS)
    root = ET.Element(f"{{{SVG_NS}}}svg", {"width": str(width), "height": str(height),
                                          "viewBox": f"0 0 {width} {height}"})
    if background:
        ET.SubElement(root, f"{{{SVG_NS}}}rect",
                      {"width": "100%", "height": "100%", "fill": background})
    for element in check_elements(elements):
        node = ET.SubElement(root, f"{{{SVG_NS}}}{element['type']}", attributes(element))
        if element["type"] == "text":
            node.text = str(element.get("text", ""))
    return ET.tostring(root, encoding="unicode")


def write_text(content: str, output_path: str) -> None:
    """Write text output (UTF-8)."""
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(content)
