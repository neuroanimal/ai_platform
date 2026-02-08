from typing import Any, Dict
from code.common.protocol.base import ProtocolAdapter

class MCPAdapter(ProtocolAdapter):
    """Model Context Protocol adapter."""

    def __init__(self):
        self.connected = False
        self.context = {}

    def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send MCP message."""
        if not self.connected:
            raise RuntimeError("Not connected")
        return {"status": "sent", "protocol": "MCP", "message": message}

    def receive(self) -> Dict[str, Any]:
        """Receive MCP message."""
        if not self.connected:
            raise RuntimeError("Not connected")
        return {"status": "received", "protocol": "MCP"}

    def connect(self, config: Dict[str, Any]) -> None:
        """Connect to MCP endpoint."""
        self.context = config
        self.connected = True

    def disconnect(self) -> None:
        """Disconnect from MCP."""
        self.connected = False
        self.context = {}
