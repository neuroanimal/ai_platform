from abc import ABC, abstractmethod
from typing import Any, Dict, List

class EvaluationAdapter(ABC):
    """Base evaluation tool adapter interface."""

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def evaluate(self, predictions: List[Any], references: List[Any], **kwargs) -> Dict[str, Any]:
        pass

    @abstractmethod
    def shutdown(self) -> None:
        pass
