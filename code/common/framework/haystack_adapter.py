from typing import Any, Dict
from ai_platform.common.framework.base import FrameworkAdapter

class HaystackAdapter(FrameworkAdapter):
    def __init__(self):
        self.initialized = False
        self.pipeline_config = {}
        self.documents_processed = 0

    def initialize(self, config: Dict[str, Any]) -> None:
        self.pipeline_config = config.get("pipeline", {})
        self.initialized = True

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        self.documents_processed += 1
        return {
            "framework": "Haystack",
            "pipeline": self.pipeline_config.get("type", "default"),
            "documents_processed": self.documents_processed,
            "result": task
        }

    def shutdown(self) -> None:
        self.initialized = False
        self.pipeline_config = {}
        self.documents_processed = 0
