"""PGVector (PostgreSQL) vector database adapter implementation."""
from typing import Any, Dict, List
from code.common.vectordb.base import VectorDBAdapter

class PGVectorAdapter(VectorDBAdapter):
    """Adapter for PGVector (PostgreSQL with vector extension)."""

    def __init__(self):
        """Initialize PGVector adapter."""
        self.connected = False

    def connect(self, config: Dict[str, Any]) -> None:
        """Connect to PGVector."""
        self.connected = True

    def insert(self, vectors: List[List[float]], metadata: List[Dict[str, Any]]) -> None:
        """Insert vectors into PGVector."""
        if not self.connected:
            raise RuntimeError("Not connected")

    def search(self, query_vector: List[float], top_k: int) -> List[Dict[str, Any]]:
        """Search for similar vectors in PGVector."""
        if not self.connected:
            raise RuntimeError("Not connected")
        return [{"db": "PGVector", "score": 0.9}]

    def disconnect(self) -> None:
        """Disconnect from PGVector."""
        self.connected = False
