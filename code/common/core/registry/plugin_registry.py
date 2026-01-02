from typing import Dict, Any

from .registry_contract import RegistryContract
from .registry_exception import (
    PluginAlreadyRegisteredError,
    PluginNotFoundError,
)


class PluginRegistry(RegistryContract):
    """
    Deterministic in-memory plugin registry.

    No auto-discovery.
    No side effects.
    Explicit registration only.
    """

    def __init__(self) -> None:
        self._plugins: Dict[str, Any] = {}

    def register(self, key: str, plugin: Any) -> None:
        if key in self._plugins:
            raise PluginAlreadyRegisteredError(key)
        self._plugins[key] = plugin

    def get(self, key: str) -> Any:
        if key not in self._plugins:
            raise PluginNotFoundError(key)
        return self._plugins[key]

    def list(self) -> Dict[str, Any]:
        return dict(self._plugins)
