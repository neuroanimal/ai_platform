"""svgwrite adapter (https://pypi.org/project/svgwrite/).

Builds the drawing with ``svgwrite.Drawing`` (imported lazily) from the
element model in ``svg_support.py``; svgwrite validates attribute names
and values against the SVG profile (``profile``: "full" or "tiny").
``save`` writes the markup; ``create`` returns it.

Not verified against an installed svgwrite here (the package was not
installed when this was written); ``NativeSVGAdapter`` produces equivalent
markup without the dependency. Previously a stub that wrapped the input in
an <svg> tag and saved nothing; the class name and the SVGAdapter methods
are unchanged.
"""

from typing import Any, Dict

from ai_platform.common.svg.base import SVGAdapter
from ai_platform.common.svg.svg_support import SVGError, attributes, check_elements, write_text


class SvgwriteAdapter(SVGAdapter):
    """SVG built with svgwrite."""

    def __init__(self):
        self.initialized = False
        self.profile = "full"
        self._svgwrite = None

    def initialize(self, config: Dict[str, Any]) -> None:
        """Import svgwrite."""
        try:
            import svgwrite  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise SVGError("SvgwriteAdapter requires: pip install svgwrite") from exc
        self._svgwrite = svgwrite
        self.profile = (config or {}).get("profile", "full")
        self.initialized = True

    def create(self, elements: Any, **kwargs) -> str:
        """Markup produced by svgwrite."""
        if not self.initialized:
            raise SVGError("SvgwriteAdapter is not initialized")
        width, height = kwargs.get("width", 200), kwargs.get("height", 200)
        drawing = self._svgwrite.Drawing(size=(width, height), profile=self.profile)
        for element in check_elements(elements):
            attrs = attributes(element)
            if element["type"] == "text":
                node = drawing.text(str(element.get("text", "")), **_svgwrite_kwargs(attrs))
            else:
                node = drawing.element_factory(element["type"], **_svgwrite_kwargs(attrs))
            drawing.add(node)
        return drawing.tostring()

    def save(self, svg_content: str, output_path: str) -> None:
        """Write the markup."""
        if not self.initialized:
            raise SVGError("SvgwriteAdapter is not initialized")
        write_text(svg_content, output_path)

    def shutdown(self) -> None:
        """Nothing to release."""
        self.initialized = False


def _svgwrite_kwargs(attrs: Dict[str, str]) -> Dict[str, str]:
    """svgwrite takes "font-size" as font_size (dash -> underscore)."""
    return {key.replace("-", "_"): value for key, value in attrs.items()}
