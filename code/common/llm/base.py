from abc import ABC, abstractmethod
from typing import Any, Dict, List

class LLMAdapter(ABC):
    """Base LLM adapter interface."""

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        pass

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        pass

    @abstractmethod
    def shutdown(self) -> None:
        pass
