from typing import Any, Dict, List
from code.common.evaluation.base import EvaluationAdapter

class HumanLoopAdapter(EvaluationAdapter):
    def __init__(self):
        self.initialized = False
        self.sessions = []
        self.feedback_count = 0

    def initialize(self, config: Dict[str, Any]) -> None:
        self.initialized = True

    def evaluate(self, predictions: List[Any], references: List[Any], **kwargs) -> Dict[str, Any]:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        session_id = f"hl_session_{len(self.sessions) + 1}"
        self.sessions.append(session_id)
        self.feedback_count += len(predictions)
        return {
            "tool": "HumanLoop",
            "session_id": session_id,
            "human_feedback_collected": True,
            "feedback_items": self.feedback_count
        }

    def shutdown(self) -> None:
        self.initialized = False
        self.sessions.clear()
        self.feedback_count = 0
