from abc import ABC, abstractmethod
from typing import Any, Dict

class RegistryContract(ABC):
    """
    Architectural registry contract.

    Registry responsibilities:
    - explicit plugin registration
    - plugin lookup by key
    - lifecycle isolation
    """

    @abstractmethod
    def register(self, key: str, plugin: Any) -> None:
        pass

    @abstractmethod
    def get(self, key: str) -> Any:
        pass

    @abstractmethod
    def list(self) -> Dict[str, Any]:
        pass
