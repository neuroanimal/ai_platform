from abc import ABC, abstractmethod
from typing import Any, Dict

class ProtocolAdapter(ABC):
    """Base protocol adapter interface."""

    @abstractmethod
    def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send message via protocol."""
        pass

    @abstractmethod
    def receive(self) -> Dict[str, Any]:
        """Receive message via protocol."""
        pass

    @abstractmethod
    def connect(self, config: Dict[str, Any]) -> None:
        """Establish protocol connection."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close protocol connection."""
        pass
