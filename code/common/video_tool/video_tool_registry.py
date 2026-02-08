from typing import Dict, Type

class VideoToolRegistry:
    """Registry for video tool adapters."""

    def __init__(self):
        self._tools: Dict[str, Type] = {}

    def register(self, name: str, adapter_class: Type) -> None:
        self._tools[name] = adapter_class

    def get(self, name: str):
        if name not in self._tools:
            raise ValueError(f"Video tool '{name}' not registered")
        return self._tools[name]()

    def list(self) -> list:
        return list(self._tools.keys())

_registry = VideoToolRegistry()

def get_registry():
    return _registry
