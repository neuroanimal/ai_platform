from typing import Dict, Type

class LLMRegistry:
    """Registry for LLM adapters."""

    def __init__(self):
        self._llms: Dict[str, Type] = {}

    def register(self, name: str, adapter_class: Type) -> None:
        self._llms[name] = adapter_class

    def get(self, name: str):
        if name not in self._llms:
            raise ValueError(f"LLM '{name}' not registered")
        return self._llms[name]()

    def list(self) -> list:
        return list(self._llms.keys())

_registry = LLMRegistry()

def get_registry():
    return _registry
