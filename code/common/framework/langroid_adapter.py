from typing import Any, Dict
from code.common.framework.base import FrameworkAdapter

class LangroidAdapter(FrameworkAdapter):
    def __init__(self):
        self.initialized = False
        self.agents = {}
        self.task_history = []

    def initialize(self, config: Dict[str, Any]) -> None:
        self.agents = config.get("agents", {"main": "default_agent"})
        self.initialized = True

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        self.task_history.append(task)
        return {
            "framework": "Langroid",
            "agents": list(self.agents.keys()),
            "tasks_completed": len(self.task_history),
            "result": task
        }

    def shutdown(self) -> None:
        self.initialized = False
        self.agents = {}
        self.task_history.clear()
