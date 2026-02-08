from typing import Dict, Type

class RAGRegistry:
    """Registry for RAG stack adapters."""

    def __init__(self):
        self._stacks: Dict[str, Type] = {}

    def register(self, name: str, adapter_class: Type) -> None:
        self._stacks[name] = adapter_class

    def get(self, name: str):
        if name not in self._stacks:
            raise ValueError(f"RAG stack '{name}' not registered")
        return self._stacks[name]()

    def list(self) -> list:
        return list(self._stacks.keys())

_registry = RAGRegistry()

def get_registry():
    return _registry
