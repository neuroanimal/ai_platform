"""Unit tests of agent tools, the agent loop (scripted LLM) and the MCP bridge."""

import json
import sys

import pytest

from ai_platform.common.agent.agent_loop import ToolAgent
from ai_platform.common.agent.builtin_tools import (
    CALCULATOR,
    UNIT_CONVERTER,
    default_tools,
    rag_search_tool,
    safe_arithmetic,
)
from ai_platform.common.agent.tool import Tool, ToolError, ToolRegistry, validate_arguments
from ai_platform.common.llm.chat_result import ChatResult, ToolCall
from ai_platform.common.llm.llm_exception import LLMRequestError
from ai_platform.common.llm.openai_compatible_adapter import parse_tool_calls


@pytest.mark.parametrize("expression,value", [
    ("17 * 23 * 19", 7429), ("(48.5 - 12.25) / 0.25", 145), ("2^10", 1024), ("-3 + 5", 2),
    ("7 ÷ 2", 3.5), ("17 × 23", 391),
])
def test_safe_arithmetic(expression, value):
    assert safe_arithmetic(expression) == value


@pytest.mark.parametrize("expression", ["__import__('os')", "a + 1", "9**9**9", "[1, 2]",
                                        "10**200"])
def test_safe_arithmetic_rejects(expression):
    with pytest.raises((ValueError, SyntaxError)):
        safe_arithmetic(expression)


def test_tool_validation_and_errors():
    assert CALCULATOR.call({"expression": "1+1"}).content["result"] == 2
    assert "missing required" in CALCULATOR.call({}).error
    assert "unexpected property" in CALCULATOR.call({"expression": "1", "x": 1}).error
    assert "expected string" in CALCULATOR.call({"expression": 5}).error
    assert UNIT_CONVERTER.call({"value": 77, "from_unit": "F", "to_unit": "C"}).content[
        "result"] == 25
    assert "cannot convert" in UNIT_CONVERTER.call(
        {"value": 1, "from_unit": "kg", "to_unit": "m"}).error
    assert validate_arguments(True, {"type": "integer"})  # bool is not an integer
    with pytest.raises(ToolError):
        Tool("bad name!", "d", {"type": "object"}, lambda: None)
    with pytest.raises(ToolError):
        ToolRegistry([CALCULATOR, CALCULATOR])


def test_parse_tool_calls():
    calls = parse_tool_calls([
        {"id": "a", "function": {"name": "calculator", "arguments": '{"expression": "1"}'}},
        {"function": {"name": "x", "arguments": {"k": 1}}},
        {"function": {"name": "y", "arguments": "not json"}},
    ])
    assert calls[0].arguments == {"expression": "1"} and calls[1].arguments == {"k": 1}
    assert calls[1].call_id == "call_1" and calls[2].arguments_error


class ScriptedLLM:
    """Returns scripted ChatResults; records what it received."""

    def __init__(self, replies, reject_tools=False):
        self.replies = list(replies)
        self.reject_tools = reject_tools
        self.calls = []

    def chat_completion(self, messages, **kwargs):
        """Next scripted reply."""
        self.calls.append({"messages": [dict(m) for m in messages], **kwargs})
        if self.reject_tools and "tools" in kwargs:
            raise LLMRequestError("model does not support tools", 400)
        return self.replies.pop(0)


def native_call(name, arguments, call_id="c1"):
    """ChatResult requesting one tool call."""
    return ChatResult(text="", model="m", finish_reason="tool_calls", tool_calls=[
        ToolCall(call_id, name, arguments, json.dumps(arguments))])


def test_native_loop_runs_tool_and_answers():
    llm = ScriptedLLM([native_call("calculator", {"expression": "17*23*19"}),
                       ChatResult(text="7429", model="m")])
    run = ToolAgent(llm, ToolRegistry(default_tools()), mode="native").run("17*23*19?")
    assert run.answer == "7429" and run.stop_reason == "answered"
    assert run.tools_used == ["calculator"] and run.steps[0].tool_calls[0]["ok"]
    second = llm.calls[1]["messages"]
    assert second[-2]["tool_calls"][0]["function"]["name"] == "calculator"
    assert second[-1]["role"] == "tool" and "7429" in second[-1]["content"]
    assert llm.calls[0]["tools"][0]["function"]["name"] == "calculator"


def test_errors_go_back_to_the_model():
    llm = ScriptedLLM([native_call("nope", {}), native_call("calculator", {"expr": "1"}),
                       ChatResult(text="done", model="m")])
    run = ToolAgent(llm, ToolRegistry(default_tools()), mode="native").run("q")
    results = [s.tool_calls[0] for s in run.steps[:2]]
    assert not results[0]["ok"] and "unknown tool" in results[0]["result"]
    assert not results[1]["ok"] and "invalid arguments" in results[1]["result"]
    assert run.answer == "done"


def test_max_steps_and_side_effects():
    writes = []
    writer = Tool("write_file", "writes", {"type": "object", "properties": {}},
                  lambda: writes.append(1), side_effects=True)
    llm = ScriptedLLM([native_call("write_file", {}) for _ in range(3)])
    run = ToolAgent(llm, ToolRegistry([writer]), mode="native", max_steps=3).run("q")
    assert run.stop_reason == "max_steps" and writes == []
    assert "side effects" in run.steps[0].tool_calls[0]["result"]


def test_json_mode_and_auto_fallback():
    replies = [ChatResult(text='```json\n{"tool": "calculator", "arguments": '
                               '{"expression": "6*7"}}\n```', model="m"),
               ChatResult(text='{"answer": "42"}', model="m")]
    llm = ScriptedLLM(replies, reject_tools=True)
    run = ToolAgent(llm, ToolRegistry(default_tools()), mode="auto").run("6*7?")
    assert run.answer == "42" and run.tools_used == ["calculator"]
    assert [s.mode for s in run.steps] == ["json", "json"]
    assert "Available tools" in llm.calls[1]["messages"][0]["content"]
    assert "returned" in llm.calls[2]["messages"][-1]["content"]


def test_rag_search_tool():
    class FakeRag:
        """retrieve() double."""
        def retrieve(self, query, top_k):
            """One hit."""
            return [{"document_id": "d", "text": f"about {query}", "score": 0.9}][:top_k]

    tool = rag_search_tool(FakeRag())
    assert tool.call({"query": "x"}).content == [{"document_id": "d", "text": "about x",
                                                  "score": 0.9}]


MCP_SERVER = '''
from mcp.server.mcpserver import MCPServer
server = MCPServer("t")

@server.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two integers."""
    return a * b

if __name__ == "__main__":
    server.run()
'''


def test_mcp_tools_in_agent(tmp_path):
    try:
        import mcp.server.mcpserver  # noqa: F401 pylint: disable=import-outside-toplevel,unused-import
    except ImportError:
        pytest.skip("mcp 2.x not installed")
    from ai_platform.common.agent.mcp_tools import tools_from_mcp  # pylint: disable=import-outside-toplevel
    from ai_platform.common.protocol.mcp_adapter import MCPAdapter  # pylint: disable=import-outside-toplevel
    script = tmp_path / "server.py"
    script.write_text(MCP_SERVER, encoding="utf-8")
    client = MCPAdapter()
    client.connect({"command": sys.executable, "args": [str(script)], "timeout": 30})
    try:
        tools = tools_from_mcp(client, read_only=["multiply"])
        assert [t.name for t in tools] == ["multiply"] and not tools[0].side_effects
        llm = ScriptedLLM([native_call("multiply", {"a": 17, "b": 23}),
                           ChatResult(text="391", model="m")])
        run = ToolAgent(llm, ToolRegistry(tools), mode="native").run("17*23?")
        assert run.steps[0].tool_calls[0]["ok"] and "391" in run.steps[0].tool_calls[0]["result"]
        assert not tools_from_mcp(client)[0].call({"a": "x", "b": 1}).ok  # schema check
    finally:
        client.disconnect()
