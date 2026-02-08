from typing import Any, Dict
from code.common.framework.base import FrameworkAdapter

class LangDockAdapter(FrameworkAdapter):
    def __init__(self):
        self.initialized = False
        self.workspace_id = None
        self.deployments = []

    def initialize(self, config: Dict[str, Any]) -> None:
        self.workspace_id = config.get("workspace_id", "default_workspace")
        self.initialized = True

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        self.deployments.append(task)
        return {
            "framework": "LangDock",
            "workspace_id": self.workspace_id,
            "deployments": len(self.deployments),
            "result": task
        }

    def shutdown(self) -> None:
        self.initialized = False
        self.workspace_id = None
        self.deployments.clear()
