"""
The agent loop: let a model use tools until it can answer.

One ``run(question)``:

1. send the conversation and the tool definitions to the model;
2. if the model answers with text and no tool calls -> done, that is the answer;
3. otherwise run each requested tool (arguments validated against the tool's
   schema; errors become tool results the model can react to), append the
   calls and their results to the conversation, and go back to 1.

Bounded by ``max_steps`` model calls and ``max_seconds`` wall time; when a
bound is hit the run stops with ``stop_reason`` saying which. Every step is
recorded in ``AgentRun.steps`` (what the model asked for, what each tool
returned, how long it took), so a run can be inspected afterwards.

Two modes, because not every local model supports the tools protocol:

- ``native``: OpenAI ``tools`` parameter; the model returns ``tool_calls``;
- ``json``: the tool list is described in the system prompt and the model
  must reply with a single JSON object ``{"tool": name, "arguments": {...}}``
  to call a tool, or ``{"answer": "..."}`` to finish. Replies that are not
  such an object are treated as the final answer.

``auto`` uses ``native`` and falls back to ``json`` for the rest of the run
when the server rejects the ``tools`` parameter.

Tools with ``side_effects=True`` are refused unless the agent was created
with ``allow_side_effects=True``.
"""

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ai_platform.common.agent.tool import ToolRegistry, ToolResult
from ai_platform.common.llm.chat_result import ToolCall
from ai_platform.common.llm.llm_exception import LLMError, LLMRequestError

MODES = ("native", "json", "auto")

JSON_PROTOCOL = """You can use tools. To call a tool, reply with ONLY one JSON object:
{{"tool": "<tool name>", "arguments": {{...}}}}
After the tool result arrives you may call another tool. When you can answer, reply with
ONLY: {{"answer": "<your final answer>"}}

Available tools:
{tools}"""


@dataclass
class AgentStep:
    """One model call and the tool calls it requested."""

    step: int
    mode: str
    model_text: str
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    elapsed_seconds: float = 0.0


@dataclass
class AgentRun:
    """Result and trace of one agent run."""

    question: str
    answer: Optional[str]
    stop_reason: str
    steps: List[AgentStep] = field(default_factory=list)
    elapsed_seconds: float = 0.0

    @property
    def tools_used(self) -> List[str]:
        """Names of the tools called, in order."""
        return [call["name"] for step in self.steps for call in step.tool_calls]

    def to_dict(self) -> Dict[str, Any]:
        """JSON-serializable trace."""
        return {"question": self.question, "answer": self.answer,
                "stop_reason": self.stop_reason, "tools_used": self.tools_used,
                "elapsed_seconds": round(self.elapsed_seconds, 3),
                "steps": [step.__dict__ for step in self.steps]}


class ToolAgent:  # pylint: disable=too-few-public-methods
    """Runs the agent loop for one LLM adapter and one tool registry."""

    def __init__(self, llm, tools: ToolRegistry, *, mode: str = "auto",  # pylint: disable=too-many-arguments
                 max_steps: int = 5, max_seconds: float = 300.0, system_prompt: str = "",
                 allow_side_effects: bool = False) -> None:
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        self.llm = llm
        self.tools = tools
        self.mode = mode
        self.max_steps = max_steps
        self.max_seconds = max_seconds
        self.system_prompt = system_prompt
        self.allow_side_effects = allow_side_effects

    def run(self, question: str) -> AgentRun:
        """Answer ``question``, using tools as the model requests."""
        mode = "native" if self.mode in ("native", "auto") else "json"
        messages = self._initial_messages(question, mode)
        run = AgentRun(question=question, answer=None, stop_reason="max_steps")
        start = time.perf_counter()
        for number in range(1, self.max_steps + 1):
            if time.perf_counter() - start > self.max_seconds:
                run.stop_reason = "max_seconds"
                break
            try:
                result, mode = self._call_model(messages, mode, question)
            except LLMError as exc:
                run.stop_reason = f"llm_error: {type(exc).__name__}: {exc}"
                break
            calls = result.tool_calls if mode == "native" else _json_calls(result.text)
            step = AgentStep(number, mode, result.text, elapsed_seconds=result.elapsed_seconds)
            run.steps.append(step)
            if calls is None or not calls:
                run.answer = _json_answer(result.text) if mode == "json" else result.text
                run.stop_reason = "answered"
                break
            messages.extend(self._execute(calls, mode, step, result.text))
        run.elapsed_seconds = time.perf_counter() - start
        return run

    # -- helpers ----------------------------------------------------------------

    def _initial_messages(self, question: str, mode: str) -> List[Dict[str, Any]]:
        system = self.system_prompt
        if mode == "json":
            system = (system + "\n\n" if system else "") + self._json_protocol()
        messages = [{"role": "system", "content": system}] if system else []
        return messages + [{"role": "user", "content": question}]

    def _json_protocol(self) -> str:
        lines = [f"- {t['function']['name']}: {t['function']['description']} "
                 f"Arguments schema: {json.dumps(t['function']['parameters'])}"
                 for t in self.tools.schemas()]
        return JSON_PROTOCOL.format(tools="\n".join(lines))

    def _call_model(self, messages, mode, question):
        if mode == "native":
            try:
                return self.llm.chat_completion(messages, tools=self.tools.schemas(),
                                                allow_empty=True), "native"
            except LLMRequestError:
                if self.mode != "auto":
                    raise
                # The server does not accept tools: restart the conversation in json mode.
                messages[:] = self._initial_messages(question, "json")
                mode = "json"
        return self.llm.chat_completion(messages, allow_empty=True), mode

    def _execute(self, calls: List[ToolCall], mode: str, step: AgentStep,
                 model_text: str) -> List[Dict[str, Any]]:
        """Run the calls; return the messages to append to the conversation."""
        results = []
        for call in calls:
            begin = time.perf_counter()
            result = self._run_tool(call)
            step.tool_calls.append({"name": call.name, "arguments": call.arguments,
                                    "ok": result.ok, "result": result.to_text()[:2000],
                                    "seconds": round(time.perf_counter() - begin, 4)})
            results.append(result)
        if mode == "native":
            appended = [{"role": "assistant", "content": model_text or "",
                         "tool_calls": [c.to_message() for c in calls]}]
            appended += [{"role": "tool", "tool_call_id": c.call_id, "name": c.name,
                          "content": r.to_text()} for c, r in zip(calls, results)]
            return appended
        return [{"role": "assistant", "content": model_text},
                {"role": "user", "content": f"Tool {calls[0].name} returned: "
                                            f"{results[0].to_text()}"}]

    def _run_tool(self, call: ToolCall) -> ToolResult:
        if call.arguments_error:
            return ToolResult(False, None, call.arguments_error)
        tool = self.tools.get(call.name)
        if tool is None:
            return ToolResult(False, None, f"unknown tool {call.name!r}; "
                                           f"available: {self.tools.names()}")
        if tool.side_effects and not self.allow_side_effects:
            return ToolResult(False, None, f"tool {call.name!r} has side effects and is "
                                           "not allowed in this agent")
        return tool.call(call.arguments)


_JSON_OBJECT = re.compile(r"\{.*\}", re.S)


def _json_object(text: str) -> Optional[Dict[str, Any]]:
    """The JSON object in a reply (code fences and surrounding prose tolerated)."""
    match = _JSON_OBJECT.search(text or "")
    if not match:
        return None
    try:
        value = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _json_calls(text: str) -> Optional[List[ToolCall]]:
    """json mode: one tool call, or None when the reply is not a tool call."""
    obj = _json_object(text)
    if not obj or "tool" not in obj:
        return None
    arguments = obj.get("arguments", {})
    error = None if isinstance(arguments, dict) else "arguments must be a JSON object"
    return [ToolCall(call_id="json_call", name=str(obj["tool"]),
                     arguments=arguments if isinstance(arguments, dict) else {},
                     raw_arguments=json.dumps(arguments), arguments_error=error)]


def _json_answer(text: str) -> str:
    """json mode: the 'answer' field, else the reply itself."""
    obj = _json_object(text)
    if obj and "answer" in obj:
        return str(obj["answer"])
    return text
