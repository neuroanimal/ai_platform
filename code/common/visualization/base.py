from abc import ABC, abstractmethod
from typing import Any, Dict

class VisualizationAdapter(ABC):
    """Base visualization library adapter interface."""

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def plot(self, data: Any, plot_type: str, **kwargs) -> Any:
        pass

    @abstractmethod
    def save(self, output_path: str) -> None:
        pass

    @abstractmethod
    def shutdown(self) -> None:
        pass
