from abc import ABC, abstractmethod
from typing import Any, Dict

class MLAdapter(ABC):
    """Base ML framework adapter interface."""

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def train(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        pass

    @abstractmethod
    def predict(self, data: Any, **kwargs) -> Any:
        pass

    @abstractmethod
    def save_model(self, path: str) -> None:
        pass

    @abstractmethod
    def load_model(self, path: str) -> None:
        pass

    @abstractmethod
    def shutdown(self) -> None:
        pass
