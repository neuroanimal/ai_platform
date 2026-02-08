from abc import ABC, abstractmethod
from typing import Any, Dict

class VisualizationToolAdapter(ABC):
    """Base visualization tool adapter interface."""

    @abstractmethod
    def connect(self, config: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def create_dashboard(self, data: Any, **kwargs) -> str:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass
