from typing import Any, Dict, List
from ai_platform.common.evaluation.base import EvaluationAdapter

class WandBAdapter(EvaluationAdapter):
    def __init__(self):
        self.initialized = False
        self.project = None
        self.runs = []
        self.artifacts_logged = 0

    def initialize(self, config: Dict[str, Any]) -> None:
        self.project = config.get("project", "default_project")
        self.initialized = True

    def evaluate(self, predictions: List[Any], references: List[Any], **kwargs) -> Dict[str, Any]:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        run_id = f"wandb_run_{len(self.runs) + 1}"
        self.runs.append(run_id)
        self.artifacts_logged += 2
        return {
            "tool": "WandB",
            "project": self.project,
            "run_id": run_id,
            "logged": True,
            "artifacts_logged": self.artifacts_logged
        }

    def shutdown(self) -> None:
        self.initialized = False
        self.project = None
        self.runs.clear()
        self.artifacts_logged = 0
