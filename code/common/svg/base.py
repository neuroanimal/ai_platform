from abc import ABC, abstractmethod
from typing import Any, Dict

class SVGAdapter(ABC):
    """Base SVG adapter interface."""

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def create(self, elements: Any, **kwargs) -> str:
        pass

    @abstractmethod
    def save(self, svg_content: str, output_path: str) -> None:
        pass

    @abstractmethod
    def shutdown(self) -> None:
        pass
