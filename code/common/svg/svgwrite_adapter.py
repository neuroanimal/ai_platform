from typing import Any, Dict
from code.common.svg.base import SVGAdapter

class SvgwriteAdapter(SVGAdapter):
    def __init__(self):
        self.initialized = False

    def initialize(self, config: Dict[str, Any]) -> None:
        self.initialized = True

    def create(self, elements: Any, **kwargs) -> str:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        return f'<svg xmlns="http://www.w3.org/2000/svg">{elements}</svg>'

    def save(self, svg_content: str, output_path: str) -> None:
        if not self.initialized:
            raise RuntimeError("Not initialized")

    def shutdown(self) -> None:
        self.initialized = False
