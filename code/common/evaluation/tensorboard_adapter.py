from typing import Any, Dict, List
from ai_platform.common.evaluation.base import EvaluationAdapter

class TensorBoardAdapter(EvaluationAdapter):
    def __init__(self):
        self.initialized = False
        self.log_dir = None
        self.scalars_logged = 0

    def initialize(self, config: Dict[str, Any]) -> None:
        self.log_dir = config.get("log_dir", "./logs")
        self.initialized = True

    def evaluate(self, predictions: List[Any], references: List[Any], **kwargs) -> Dict[str, Any]:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        self.scalars_logged += 3
        return {
            "tool": "TensorBoard",
            "log_dir": self.log_dir,
            "logged": True,
            "scalars_logged": self.scalars_logged
        }

    def shutdown(self) -> None:
        self.initialized = False
        self.log_dir = None
        self.scalars_logged = 0
