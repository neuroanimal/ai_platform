from typing import Any, Dict, List
from code.common.framework.base import FrameworkAdapter

class GriptapeAdapter(FrameworkAdapter):
    def __init__(self):
        self.initialized = False
        self.tasks: List[Dict[str, Any]] = []
        self.config = {}

    def initialize(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.initialized = True

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        self.tasks.append(task)
        return {
            "framework": "Griptape",
            "task_id": len(self.tasks),
            "status": "completed",
            "result": task,
            "tools_used": self.config.get("tools", [])
        }

    def shutdown(self) -> None:
        self.initialized = False
        self.tasks.clear()
        self.config = {}
