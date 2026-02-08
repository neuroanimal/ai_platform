from typing import Any, Dict
from code.common.protocol.base import ProtocolAdapter

class ACPAdapter(ProtocolAdapter):
    """Agent Communication Protocol adapter."""

    def __init__(self):
        self.connected = False
        self.agents = []

    def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send ACP message."""
        if not self.connected:
            raise RuntimeError("Not connected")
        return {"status": "sent", "protocol": "ACP", "message": message}

    def receive(self) -> Dict[str, Any]:
        """Receive ACP message."""
        if not self.connected:
            raise RuntimeError("Not connected")
        return {"status": "received", "protocol": "ACP"}

    def connect(self, config: Dict[str, Any]) -> None:
        """Connect to ACP network."""
        self.agents = config.get("agents", [])
        self.connected = True

    def disconnect(self) -> None:
        """Disconnect from ACP."""
        self.connected = False
        self.agents = []
