"""Example usage of protocol (MCP, ACP, A2A) adapters.

Registers every adapter and exercises each one with a small, real
operation - MCP against a tiny stdio server started from
this example. Nothing is fabricated: an adapter whose tool, server or
package is not available here is reported as skipped with the reason.

    python -m ai_platform.common.example.protocol_example
"""

# Examples follow the same register-and-try pattern on purpose.
# pylint: disable=duplicate-code

import os
import sys
import tempfile

from ai_platform.common.protocol.a2a_adapter import A2AAdapter
from ai_platform.common.protocol.acp_adapter import ACPAdapter
from ai_platform.common.protocol.mcp_adapter import MCPAdapter
from ai_platform.common.protocol.mcp_adapter import ProtocolError
from ai_platform.common.protocol.protocol_registry import get_registry


def main():
    """Register all adapters and exercise the usable ones."""
    registry = get_registry()

    tools = {
        "mcp": MCPAdapter,
        "acp": ACPAdapter,
        "a2a": A2AAdapter,
    }

    for name, adapter_class in tools.items():
        registry.register(name, adapter_class)

    print(f"Registered {len(tools)}: {registry.list()}\n")

    server_code = (
        "from mcp.server.mcpserver import MCPServer\n"
        "server = MCPServer('example')\n"
        "@server.tool()\n"
        "def multiply(a: int, b: int) -> int:\n"
        "    return a * b\n"
        "server.run()\n")
    with tempfile.TemporaryDirectory() as tmp:
        script = os.path.join(tmp, "server.py")
        with open(script, "w", encoding="utf-8") as handle:
            handle.write(server_code)
        configs = {"mcp": {"command": sys.executable, "args": [script]},
                   "acp": {"url": "http://127.0.0.1:8000"},
                   "a2a": {"url": "http://127.0.0.1:9999"}}
        messages = {"mcp": {"method": "tools/call",
                            "params": {"name": "multiply", "arguments": {"a": 17, "b": 23}}},
                    "acp": {"text": "17*23"}, "a2a": {"text": "17*23"}}
        for name in tools:
            adapter = registry.get(name)
            try:
                adapter.connect(configs[name])
                print(f"{name:5} OK      {str(adapter.send(messages[name]))[:90]}")
            except ProtocolError as exc:
                print(f"{name:5} skipped {type(exc).__name__}: {str(exc)[:80]}")
            finally:
                adapter.disconnect()


if __name__ == "__main__":
    main()
