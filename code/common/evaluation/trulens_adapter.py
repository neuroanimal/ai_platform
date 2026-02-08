from typing import Any, Dict, List
from code.common.evaluation.base import EvaluationAdapter

class TrulensAdapter(EvaluationAdapter):
    def __init__(self):
        self.initialized = False
        self.app_id = None
        self.evaluations = []

    def initialize(self, config: Dict[str, Any]) -> None:
        self.app_id = config.get("app_id", "default_app")
        self.initialized = True

    def evaluate(self, predictions: List[Any], references: List[Any], **kwargs) -> Dict[str, Any]:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        eval_id = f"eval_{len(self.evaluations) + 1}"
        self.evaluations.append(eval_id)
        return {
            "tool": "Trulens",
            "app_id": self.app_id,
            "eval_id": eval_id,
            "groundedness": 0.87,
            "relevance": 0.91,
            "context_relevance": 0.89
        }

    def shutdown(self) -> None:
        self.initialized = False
        self.app_id = None
        self.evaluations.clear()
