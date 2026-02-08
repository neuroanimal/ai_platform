"""Vector database registry for managing adapter implementations."""
from typing import Dict, Type

class VectorDBRegistry:
    """Registry for vector database adapters."""

    def __init__(self):
        """Initialize the registry."""
        self._dbs: Dict[str, Type] = {}

    def register(self, name: str, adapter_class: Type) -> None:
        """Register a vector database adapter."""
        self._dbs[name] = adapter_class

    def get(self, name: str):
        """Get a vector database adapter by name."""
        if name not in self._dbs:
            raise ValueError(f"VectorDB '{name}' not registered")
        return self._dbs[name]()

    def list(self) -> list:
        """List all registered vector database names."""
        return list(self._dbs.keys())

_registry = VectorDBRegistry()

def get_registry():
    """Get the global vector database registry."""
    return _registry
