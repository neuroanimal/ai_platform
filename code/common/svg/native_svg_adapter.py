"""Native SVG adapter (new; add-only): stdlib ElementTree, no dependency.

``create(elements, width=200, height=200, background="")`` returns SVG
markup for the element model in ``svg_support.py``; ``save`` writes it.
"""

from typing import Any, Dict

from ai_platform.common.svg.base import SVGAdapter
from ai_platform.common.svg.svg_support import SVGError, build_svg, write_text


class NativeSVGAdapter(SVGAdapter):
    """SVG markup without third-party packages."""

    def __init__(self):
        self.initialized = False
        self.defaults: Dict[str, Any] = {}

    def initialize(self, config: Dict[str, Any]) -> None:
        """Default width/height/background for create()."""
        self.defaults = {k: v for k, v in (config or {}).items()
                         if k in ("width", "height", "background")}
        self.initialized = True

    def create(self, elements: Any, **kwargs) -> str:
        """SVG markup for ``elements``."""
        self._require()
        return build_svg(elements, **{**self.defaults, **kwargs})

    def save(self, svg_content: str, output_path: str) -> None:
        """Write the markup."""
        self._require()
        write_text(svg_content, output_path)

    def shutdown(self) -> None:
        """Nothing to release."""
        self.initialized = False

    def _require(self) -> None:
        if not self.initialized:
            raise SVGError(f"{type(self).__name__} is not initialized")
