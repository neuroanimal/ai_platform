from typing import Dict, Type

class VisualizationRegistry:
    """Registry for visualization library adapters."""

    def __init__(self):
        self._libraries: Dict[str, Type] = {}

    def register(self, name: str, adapter_class: Type) -> None:
        self._libraries[name] = adapter_class

    def get(self, name: str):
        if name not in self._libraries:
            raise ValueError(f"Visualization library '{name}' not registered")
        return self._libraries[name]()

    def list(self) -> list:
        return list(self._libraries.keys())

_registry = VisualizationRegistry()

def get_registry():
    return _registry
