from typing import Any, Dict, List
from ai_platform.common.evaluation.base import EvaluationAdapter

class LangSmithAdapter(EvaluationAdapter):
    def __init__(self):
        self.initialized = False
        self.project_name = None
        self.traces = []

    def initialize(self, config: Dict[str, Any]) -> None:
        self.project_name = config.get("project_name", "default_project")
        self.initialized = True

    def evaluate(self, predictions: List[Any], references: List[Any], **kwargs) -> Dict[str, Any]:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        trace_id = f"trace_{len(self.traces) + 1}"
        self.traces.append(trace_id)
        return {
            "tool": "LangSmith",
            "project": self.project_name,
            "trace_id": trace_id,
            "traced": True,
            "dataset_id": f"dataset_{len(self.traces)}"
        }

    def shutdown(self) -> None:
        self.initialized = False
        self.project_name = None
        self.traces.clear()
