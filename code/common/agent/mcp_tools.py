"""
Expose the tools of an MCP server as agent tools.

``tools_from_mcp(client)`` lists the server's tools (``tools/list``) on a
connected ``MCPAdapter`` and wraps each as a ``Tool`` whose function sends
``tools/call``. The server's input schema becomes the tool's parameter
schema, so arguments are validated locally before anything is sent.

MCP tools are marked ``side_effects=True`` unless the server annotates them
``readOnlyHint: true`` (MCP tool annotations) or the caller lists them in
``read_only`` - the agent then refuses them unless side effects are allowed.
"""

from typing import Iterable, List, Optional

from ai_platform.common.agent.tool import Tool


def _content_text(result) -> str:
    parts = [block.get("text", "") for block in result.get("content", [])
             if block.get("type") == "text"]
    return "\n".join(parts) if parts else str(result.get("structuredContent", result))


def tools_from_mcp(client, read_only: Optional[Iterable[str]] = None) -> List[Tool]:
    """Agent tools for every tool of the connected MCP server."""
    read_only = set(read_only or [])
    tools = []
    for spec in client.send({"method": "tools/list"}).get("tools", []):
        name = spec["name"]
        schema = spec.get("inputSchema") or {"type": "object", "properties": {}}
        hinted = (spec.get("annotations") or {}).get("readOnlyHint") is True

        def call(_name=name, **arguments):
            result = client.send({"method": "tools/call",
                                  "params": {"name": _name, "arguments": arguments}})
            if result.get("isError"):
                raise RuntimeError(_content_text(result))
            return result.get("structuredContent") or _content_text(result)

        tools.append(Tool(name=name, description=spec.get("description") or name,
                          parameters=schema, function=call,
                          side_effects=not (hinted or name in read_only),
                          metadata={"source": "mcp"}))
    return tools
