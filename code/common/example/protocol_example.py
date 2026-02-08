"""Example usage of protocol adapters."""

from code.common.protocol.protocol_registry import get_registry
from code.common.protocol.mcp_adapter import MCPAdapter
from code.common.protocol.acp_adapter import ACPAdapter
from code.common.protocol.a2a_adapter import A2AAdapter

def main():
    # Get registry
    registry = get_registry()

    # Register protocols
    registry.register("mcp", MCPAdapter)
    registry.register("acp", ACPAdapter)
    registry.register("a2a", A2AAdapter)

    print(f"Registered protocols: {registry.list()}")

    # MCP example
    print("\n=== MCP Example ===")
    mcp = registry.get("mcp")
    mcp.connect({"endpoint": "localhost:8080"})
    result = mcp.send({"type": "context", "model": "gpt-4"})
    print(f"MCP send: {result}")
    mcp.disconnect()

    # ACP example
    print("\n=== ACP Example ===")
    acp = registry.get("acp")
    acp.connect({"agents": ["agent1", "agent2"]})
    result = acp.send({"type": "broadcast", "message": "hello"})
    print(f"ACP send: {result}")
    acp.disconnect()

    # A2A example
    print("\n=== A2A Example ===")
    a2a = registry.get("a2a")
    a2a.connect({"peer_id": "agent-123"})
    result = a2a.send({"type": "direct", "data": "task"})
    print(f"A2A send: {result}")
    a2a.disconnect()

if __name__ == "__main__":
    main()
