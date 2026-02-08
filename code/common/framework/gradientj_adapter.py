from typing import Any, Dict
from code.common.framework.base import FrameworkAdapter

class GradientJAdapter(FrameworkAdapter):
    def __init__(self):
        self.initialized = False
        self.model_id = None
        self.fine_tuning_jobs = []

    def initialize(self, config: Dict[str, Any]) -> None:
        self.model_id = config.get("model_id", "base_model")
        self.initialized = True

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        if task.get("type") == "fine_tune":
            self.fine_tuning_jobs.append(task)
        return {
            "framework": "GradientJ",
            "model_id": self.model_id,
            "fine_tuning_jobs": len(self.fine_tuning_jobs),
            "result": task
        }

    def shutdown(self) -> None:
        self.initialized = False
        self.model_id = None
        self.fine_tuning_jobs.clear()
