"""
Shared base of the JavaScript SVG library adapters (Raphael, Snap.svg, SVG.js).

These libraries run in a browser, so a Python adapter cannot execute them;
what it can do for real is *generate* the JavaScript that draws the
elements with the library's own API. ``create(elements)`` returns that
JavaScript; ``save(content, path)`` writes either the script (``.js``) or a
self-contained HTML page that loads the library and runs it (``.html``).

Values are embedded with ``json.dumps``, so labels and colours cannot break
out of the generated script.

Configuration:

    library_url   script URL used in the HTML page (default: the CDN URL
                  of the version the generator was written for)
    container_id  id of the element the drawing is attached to, default "drawing"
"""

import json
import os
from typing import Any, Dict, List

from ai_platform.common.svg.base import SVGAdapter
from ai_platform.common.svg.svg_support import SVGError, check_elements, points_text, write_text

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>{title}</title>
<script src="{library_url}"></script></head>
<body>
<div id="{container}" role="img" aria-label="{title}"></div>
<script>
{script}
</script>
</body>
</html>
"""


def js(value: Any) -> str:
    """JavaScript literal of a Python value."""
    return json.dumps(value, ensure_ascii=False)


class JavaScriptSVGAdapter(SVGAdapter):
    """Generates drawing code for a browser SVG library."""

    LIBRARY = "library"
    LIBRARY_URL = ""

    def __init__(self):
        self.initialized = False
        self.library_url = self.LIBRARY_URL
        self.container_id = "drawing"

    def initialize(self, config: Dict[str, Any]) -> None:
        """Read the library URL and the container id."""
        config = dict(config or {})
        self.library_url = config.get("library_url", self.LIBRARY_URL)
        self.container_id = config.get("container_id", "drawing")
        self.initialized = True

    def create(self, elements: Any, **kwargs) -> str:
        """JavaScript that draws ``elements`` with the library."""
        self._require()
        width, height = kwargs.get("width", 200), kwargs.get("height", 200)
        lines = [self.canvas(width, height)]
        for element in check_elements(elements):
            attrs = {k: (points_text(v) if k == "points" else v)
                     for k, v in element.items() if k not in ("type", "text")}
            lines.append(self.shape(element["type"], element, attrs) + ";")
        return "\n".join(lines)

    def save(self, svg_content: str, output_path: str) -> None:
        """Write the script (.js) or an HTML page running it (.html)."""
        self._require()
        extension = os.path.splitext(output_path)[1].lower()
        if extension == ".js":
            write_text(svg_content, output_path)
        elif extension in (".html", ".htm"):
            write_text(HTML_PAGE.format(title=f"{self.LIBRARY} drawing",
                                        library_url=self.library_url,
                                        container=self.container_id, script=svg_content),
                       output_path)
        else:
            raise SVGError(f"{type(self).__name__} writes .js or .html, not {extension!r}")

    def shutdown(self) -> None:
        """Nothing to release."""
        self.initialized = False

    # -- library-specific hooks ------------------------------------------

    def canvas(self, width: Any, height: Any) -> str:
        """Statement creating the drawing surface as variable ``paper``."""
        raise NotImplementedError

    def shape(self, kind: str, element: Dict[str, Any], attrs: Dict[str, Any]) -> str:
        """Expression drawing one element on ``paper``."""
        raise NotImplementedError

    @staticmethod
    def with_attrs(expression: str, attrs: Dict[str, Any], skip: List[str]) -> str:
        """Append .attr({...}) for the attributes not already passed positionally."""
        rest = {k: v for k, v in attrs.items() if k not in skip}
        return f"{expression}.attr({js(rest)})" if rest else expression

    def _require(self) -> None:
        if not self.initialized:
            raise SVGError(f"{type(self).__name__} is not initialized")
