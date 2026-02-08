from abc import ABC, abstractmethod
from typing import Any, Dict

class ScientificToolAdapter(ABC):
    """Base scientific computing tool adapter interface."""

    @abstractmethod
    def connect(self, config: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def execute(self, script: str, **kwargs) -> Any:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass
