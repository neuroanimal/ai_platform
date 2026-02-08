from typing import Dict, Type
from code.common.protocol.base import ProtocolAdapter

class ProtocolRegistry:
    """Registry for protocol adapters."""

    def __init__(self):
        self._protocols: Dict[str, Type[ProtocolAdapter]] = {}

    def register(self, name: str, adapter_class: Type[ProtocolAdapter]) -> None:
        """Register protocol adapter."""
        self._protocols[name] = adapter_class

    def get(self, name: str) -> ProtocolAdapter:
        """Get protocol adapter instance."""
        if name not in self._protocols:
            raise ValueError(f"Protocol '{name}' not registered")
        return self._protocols[name]()

    def list(self) -> list:
        """List registered protocols."""
        return list(self._protocols.keys())

_registry = ProtocolRegistry()

def get_registry() -> ProtocolRegistry:
    """Get global protocol registry."""
    return _registry
