from abc import ABC, abstractmethod

class PluginContract(ABC):
    """
    Base contract for all plugins.

    Plugins must:
    - implement this interface
    - register themselves explicitly
    - avoid side effects on import
    """

    @abstractmethod
    def register(self, registry) -> None:
        pass
