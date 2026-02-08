from abc import ABC, abstractmethod
from typing import Any, Dict

class VideoToolAdapter(ABC):
    """Base video tool adapter interface."""

    @abstractmethod
    def connect(self, config: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def process(self, input_path: str, operations: Dict[str, Any]) -> str:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass
