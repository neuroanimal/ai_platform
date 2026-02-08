from typing import Any, Dict, List
from code.common.evaluation.base import EvaluationAdapter

class DeepEvalAdapter(EvaluationAdapter):
    def __init__(self):
        self.initialized = False

    def initialize(self, config: Dict[str, Any]) -> None:
        self.initialized = True

    def evaluate(self, predictions: List[Any], references: List[Any], **kwargs) -> Dict[str, Any]:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        return {"tool": "DeepEval", "hallucination_score": 0.05, "toxicity_score": 0.02}

    def shutdown(self) -> None:
        self.initialized = False
