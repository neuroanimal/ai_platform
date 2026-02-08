from typing import Any, Dict
from ai_platform.common.protocol.base import ProtocolAdapter

class A2AAdapter(ProtocolAdapter):
    """Agent-to-Agent Protocol adapter."""

    def __init__(self):
        self.connected = False
        self.peer_id = None

    def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send A2A message."""
        if not self.connected:
            raise RuntimeError("Not connected")
        return {"status": "sent", "protocol": "A2A", "message": message, "peer": self.peer_id}

    def receive(self) -> Dict[str, Any]:
        """Receive A2A message."""
        if not self.connected:
            raise RuntimeError("Not connected")
        return {"status": "received", "protocol": "A2A", "peer": self.peer_id}

    def connect(self, config: Dict[str, Any]) -> None:
        """Connect to A2A peer."""
        self.peer_id = config.get("peer_id")
        self.connected = True

    def disconnect(self) -> None:
        """Disconnect from A2A peer."""
        self.connected = False
        self.peer_id = None
