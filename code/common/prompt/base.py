from abc import ABC, abstractmethod
from typing import Any, Dict

class PromptAdapter(ABC):
    """Base prompt engineering adapter interface."""

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def render(self, template: str, variables: Dict[str, Any]) -> str:
        pass

    @abstractmethod
    def shutdown(self) -> None:
        pass
