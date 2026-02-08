# Protocol Support

Protocol adapters for AI agent communication.

## Supported Protocols

- **MCP** (Model Context Protocol): Context sharing between models
- **ACP** (Agent Communication Protocol): Multi-agent communication
- **A2A** (Agent-to-Agent): Direct peer-to-peer agent communication

## Usage

```python
from code.common.protocol.protocol_registry import get_registry
from code.common.protocol.mcp_adapter import MCPAdapter
from code.common.protocol.acp_adapter import ACPAdapter
from code.common.protocol.a2a_adapter import A2AAdapter

# Register protocols
registry = get_registry()
registry.register("mcp", MCPAdapter)
registry.register("acp", ACPAdapter)
registry.register("a2a", A2AAdapter)

# Use protocol
adapter = registry.get("mcp")
adapter.connect({"endpoint": "localhost:8080"})
response = adapter.send({"type": "context", "data": "..."})
adapter.disconnect()
```

## Architecture

Follows AI Platform patterns:
- Base interface: `ProtocolAdapter`
- Concrete adapters: `MCPAdapter`, `ACPAdapter`, `A2AAdapter`
- Registry pattern: `ProtocolRegistry`
- Plugin-based extensibility
