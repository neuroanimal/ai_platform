from typing import Any, Dict, Type

class FrameworkRegistry:
    """Registry for framework adapters."""

    def __init__(self):
        self._frameworks: Dict[str, Type] = {}

    def register(self, name: str, adapter_class: Type) -> None:
        self._frameworks[name] = adapter_class

    def get(self, name: str):
        if name not in self._frameworks:
            raise ValueError(f"Framework '{name}' not registered")
        return self._frameworks[name]()

    def list(self) -> list:
        return list(self._frameworks.keys())

_registry = FrameworkRegistry()

def get_registry():
    return _registry
