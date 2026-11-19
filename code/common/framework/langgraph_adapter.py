"""LangGraph adapter.

Configuration, one of:

- ``graph``: a compiled LangGraph graph; ``execute({"input": state})`` calls
  ``graph.invoke(state, config=task.get("config"))``;
- ``llm`` (platform LLM adapter): the adapter compiles a one-node graph
  (``StateGraph`` over ``{"input", "output"}``, START -> llm -> END) that
  answers ``input`` with the LLM - the minimal starting point to extend.

``output`` is ``state["output"]`` when present, else the whole final state.
Not verified against an installed LangGraph here (the package was not
installed when this was written). Previously a stub echoing the task; the
class name and the FrameworkAdapter methods are unchanged.
"""

from typing import Any, Dict

from ai_platform.common.framework.framework_support import (
    FrameworkBase,
    FrameworkError,
    require_module,
    task_input,
)


class LangGraphAdapter(FrameworkBase):
    """Runs a LangGraph graph."""

    FRAMEWORK = "LangGraph"

    def __init__(self):
        super().__init__()
        self.graph = None

    def _setup(self, config: Dict[str, Any]) -> None:
        if config.get("graph") is not None:
            self.graph = config["graph"]
            return
        llm = config.get("llm")
        if llm is None:
            raise FrameworkError("LangGraphAdapter needs 'graph' or 'llm'")
        graph_module = require_module("langgraph.graph", "langgraph")

        def answer(state: Dict[str, Any]) -> Dict[str, Any]:
            reply = llm.chat_completion([{"role": "user", "content": str(state["input"])}])
            return {"output": reply.text}

        builder = graph_module.StateGraph(dict)
        builder.add_node("llm", answer)
        builder.add_edge(graph_module.START, "llm")
        builder.add_edge("llm", graph_module.END)
        self.graph = builder.compile()

    def _run(self, task: Dict[str, Any]):
        value = task_input(task)
        state = value if isinstance(value, dict) else {"input": value}
        final = self.graph.invoke(state, config=task.get("config"))
        output = final.get("output", final) if isinstance(final, dict) else final
        return output, final
