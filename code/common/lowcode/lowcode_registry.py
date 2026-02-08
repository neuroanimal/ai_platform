from typing import Dict, Type

class LowCodeRegistry:
    """Registry for low-code/no-code platform adapters."""

    def __init__(self):
        self._platforms: Dict[str, Type] = {}

    def register(self, name: str, adapter_class: Type) -> None:
        self._platforms[name] = adapter_class

    def get(self, name: str):
        if name not in self._platforms:
            raise ValueError(f"Platform '{name}' not registered")
        return self._platforms[name]()

    def list(self) -> list:
        return list(self._platforms.keys())

_registry = LowCodeRegistry()

def get_registry():
    return _registry
