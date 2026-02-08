from abc import ABC, abstractmethod
from typing import Any, Dict

class FrameworkAdapter(ABC):
    """Base framework adapter interface."""

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def shutdown(self) -> None:
        pass
