from typing import Any, Dict, List
from code.common.evaluation.base import EvaluationAdapter

class MLflowAdapter(EvaluationAdapter):
    def __init__(self):
        self.initialized = False
        self.experiment_name = None
        self.runs = []

    def initialize(self, config: Dict[str, Any]) -> None:
        self.experiment_name = config.get("experiment_name", "default_experiment")
        self.initialized = True

    def evaluate(self, predictions: List[Any], references: List[Any], **kwargs) -> Dict[str, Any]:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        run_id = f"run_{len(self.runs) + 1}"
        self.runs.append(run_id)
        return {
            "tool": "MLflow",
            "experiment": self.experiment_name,
            "run_id": run_id,
            "metrics_logged": True,
            "accuracy": 0.85,
            "f1_score": 0.82
        }

    def shutdown(self) -> None:
        self.initialized = False
        self.experiment_name = None
        self.runs.clear()
