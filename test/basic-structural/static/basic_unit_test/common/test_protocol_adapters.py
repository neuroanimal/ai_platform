"""Tests of the protocol adapters.

MCP runs for real: a tiny MCP server (official SDK) is started as a stdio
subprocess. A2A and ACP run against an in-process fake server.
"""

import importlib.util
import os
import sys
import textwrap

import pytest

sys.path.insert(0, os.path.dirname(__file__))

from fake_json_server import FakeJsonServer  # noqa: E402

from ai_platform.common.protocol.a2a_adapter import A2AAdapter  # noqa: E402
from ai_platform.common.protocol.acp_adapter import ACPAdapter  # noqa: E402
from ai_platform.common.protocol.mcp_adapter import MCPAdapter, ProtocolError  # noqa: E402

MCP_SERVER = textwrap.dedent('''
    from mcp.server.mcpserver import MCPServer
    server = MCPServer("test-server")

    @server.tool()
    def multiply(a: int, b: int) -> int:
        """Multiply two integers."""
        return a * b

    if __name__ == "__main__":
        server.run()
''')


def has_module(name):
    """find_spec for dotted names raises when the parent package is missing."""
    try:
        return importlib.util.find_spec(name) is not None
    except ModuleNotFoundError:
        return False


@pytest.mark.skipif(not has_module("mcp.server.mcpserver"), reason="mcp 2.x not installed")
def test_mcp_stdio_roundtrip(tmp_path):
    script = tmp_path / "server.py"
    script.write_text(MCP_SERVER, encoding="utf-8")
    client = MCPAdapter()
    client.connect({"command": sys.executable, "args": [str(script)], "timeout": 30})
    try:
        assert client.server_info["serverInfo"]["name"] == "test-server"
        tools = client.send({"method": "tools/list"})["tools"]
        assert [t["name"] for t in tools] == ["multiply"]
        result = client.send({"method": "tools/call",
                              "params": {"name": "multiply", "arguments": {"a": 17, "b": 23}}})
        assert result["isError"] is False
        assert result["content"][0]["text"] == "391"
        with pytest.raises(ProtocolError, match="unsupported"):
            client.send({"method": "nope"})
    finally:
        client.disconnect()
    assert client.connected is False


def test_mcp_needs_transport():
    with pytest.raises(ProtocolError):
        MCPAdapter().connect({})


def test_a2a_card_message_and_polling():
    state = {"polls": 0}

    def rpc(_m, _p, body, headers):
        assert headers["authorization"] == "Bearer k"
        if body["method"] == "message/send":
            text = body["params"]["message"]["parts"][0]["text"]
            return 200, {"jsonrpc": "2.0", "id": body["id"], "result": {
                "kind": "task", "id": "t1", "status": {"state": "working"},
                "history": [{"parts": [{"kind": "text", "text": text}]}]}}
        state["polls"] += 1
        assert body["method"] == "tasks/get" and body["params"] == {"id": "t1"}
        return 200, {"jsonrpc": "2.0", "id": body["id"], "result": {
            "kind": "task", "id": "t1", "status": {"state": "completed"},
            "artifacts": [{"parts": [{"kind": "text", "text": "391"}]}]}}

    routes = {("GET", "/.well-known/agent-card.json"): (404, {}),
              ("GET", "/.well-known/agent.json"): lambda *a: (
                  200, {"name": "calc", "url": server.url + "/rpc"}),
              ("POST", "/rpc"): rpc}
    with FakeJsonServer(routes) as server:
        agent = A2AAdapter()
        agent.connect({"url": server.url, "api_key": "k"})
        assert agent.agent_card["name"] == "calc"
        assert agent.send({"text": "17*23"})["status"]["state"] == "working"
        done = agent.receive()
        assert done["artifacts"][0]["parts"][0]["text"] == "391"
        assert agent.receive() == {}
    assert state["polls"] == 1


def test_a2a_jsonrpc_error():
    routes = {("GET", "/.well-known/agent-card.json"): {"name": "x"},
              ("POST", "/"): {"jsonrpc": "2.0", "id": 1, "error": {"code": -32601}}}
    with FakeJsonServer(routes) as server:
        agent = A2AAdapter()
        agent.connect({"url": server.url})
        with pytest.raises(ProtocolError, match="-32601"):
            agent.send({"method": "tasks/cancel", "params": {"id": "x"}})


def test_acp_sync_run_and_async_poll():
    def runs(_m, _p, body, _h):
        assert body["agent_name"] == "echo"
        content = body["input"][0]["parts"][0]["content"]
        if body["mode"] == "sync":
            return 200, {"run_id": "r1", "status": "completed", "output": [
                {"parts": [{"content": content.upper(), "content_type": "text/plain"}]}]}
        return 202, {"run_id": "r2", "status": "in-progress"}

    routes = {("GET", "/agents"): {"agents": [{"name": "echo"}]},
              ("POST", "/runs"): runs,
              ("GET", "/runs/r2"): {"run_id": "r2", "status": "completed", "output": [
                  {"parts": [{"content": "later", "content_type": "text/plain"}]}]}}
    with FakeJsonServer(routes) as server:
        acp = ACPAdapter()
        acp.connect({"url": server.url})
        assert acp.send({"text": "hej"})["text"] == "HEJ"
        assert acp.receive() == {}
        assert acp.send({"text": "x", "mode": "async"})["status"] == "in-progress"
        assert acp.receive()["text"] == "later"
