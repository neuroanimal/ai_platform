from typing import Any, Dict, List
from code.common.evaluation.base import EvaluationAdapter

class RAGASAdapter(EvaluationAdapter):
    def __init__(self):
        self.initialized = False
        self.evaluations = []
        self.metrics_config = {}

    def initialize(self, config: Dict[str, Any]) -> None:
        self.metrics_config = config.get("metrics", {})
        self.initialized = True

    def evaluate(self, predictions: List[Any], references: List[Any], **kwargs) -> Dict[str, Any]:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        result = {
            "tool": "RAGAS",
            "faithfulness": 0.85,
            "answer_relevancy": 0.90,
            "context_precision": 0.88,
            "context_recall": 0.86,
            "evaluations_count": len(self.evaluations) + 1
        }
        self.evaluations.append(result)
        return result

    def shutdown(self) -> None:
        self.initialized = False
        self.evaluations.clear()
        self.metrics_config = {}
