"""Base interface for vector database adapters."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List

class VectorDBAdapter(ABC):
    """Base vector database adapter interface."""

    @abstractmethod
    def connect(self, config: Dict[str, Any]) -> None:
        """Connect to the vector database."""
        pass

    @abstractmethod
    def insert(self, vectors: List[List[float]], metadata: List[Dict[str, Any]]) -> None:
        """Insert vectors with metadata into the database."""
        pass

    @abstractmethod
    def search(self, query_vector: List[float], top_k: int) -> List[Dict[str, Any]]:
        """Search for similar vectors."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the vector database."""
        pass
