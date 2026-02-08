from abc import ABC, abstractmethod
from typing import Any, Dict

class LaTeXAdapter(ABC):
    """Base LaTeX/TeX adapter interface."""

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def render(self, content: str, **kwargs) -> str:
        pass

    @abstractmethod
    def compile(self, source: str, output_path: str) -> None:
        pass

    @abstractmethod
    def shutdown(self) -> None:
        pass
