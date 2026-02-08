from typing import Any, Dict
from code.common.latex.base import LaTeXAdapter

class AsymptoteAdapter(LaTeXAdapter):
    def __init__(self):
        self.initialized = False

    def initialize(self, config: Dict[str, Any]) -> None:
        self.initialized = True

    def render(self, content: str, **kwargs) -> str:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        return f"// Asymptote code\n{content}"

    def compile(self, source: str, output_path: str) -> None:
        if not self.initialized:
            raise RuntimeError("Not initialized")

    def shutdown(self) -> None:
        self.initialized = False
