from typing import Any, Dict
from code.common.lowcode.base import LowCodeAdapter

class LangFlowAdapter(LowCodeAdapter):
    def __init__(self):
        self.connected = False

    def connect(self, config: Dict[str, Any]) -> None:
        self.connected = True

    def deploy_workflow(self, workflow: Dict[str, Any]) -> str:
        if not self.connected:
            raise RuntimeError("Not connected")
        return f"langflow-workflow-{workflow.get('name', 'default')}"

    def execute_workflow(self, workflow_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        if not self.connected:
            raise RuntimeError("Not connected")
        return {"platform": "LangFlow", "workflow_id": workflow_id, "status": "completed"}

    def disconnect(self) -> None:
        self.connected = False
