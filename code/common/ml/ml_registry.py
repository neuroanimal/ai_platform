from typing import Dict, Type

class MLRegistry:
    """Registry for ML framework adapters."""

    def __init__(self):
        self._frameworks: Dict[str, Type] = {}

    def register(self, name: str, adapter_class: Type) -> None:
        self._frameworks[name] = adapter_class

    def get(self, name: str):
        if name not in self._frameworks:
            raise ValueError(f"ML framework '{name}' not registered")
        return self._frameworks[name]()

    def list(self) -> list:
        return list(self._frameworks.keys())

_registry = MLRegistry()

def get_registry():
    return _registry
