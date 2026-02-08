from typing import Any, Dict
from code.common.framework.base import FrameworkAdapter

class LangGraphAdapter(FrameworkAdapter):
    """LangGraph framework adapter."""

    def __init__(self):
        self.initialized = False
        self.graph = None

    def initialize(self, config: Dict[str, Any]) -> None:
        self.graph = config.get("graph_type", "default")
        self.initialized = True

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        return {"framework": "LangGraph", "graph": self.graph, "result": task}

    def shutdown(self) -> None:
        self.initialized = False
        self.graph = None
