from abc import ABC, abstractmethod
from typing import Any, Dict, List

class RAGAdapter(ABC):
    """Base RAG stack adapter interface."""

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def ingest(self, documents: List[Dict[str, Any]]) -> None:
        pass

    @abstractmethod
    def query(self, question: str, **kwargs) -> Dict[str, Any]:
        pass

    @abstractmethod
    def shutdown(self) -> None:
        pass
