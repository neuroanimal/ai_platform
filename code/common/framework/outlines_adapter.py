from typing import Any, Dict
from ai_platform.common.framework.base import FrameworkAdapter

class OutlinesAdapter(FrameworkAdapter):
    def __init__(self):
        self.initialized = False
        self.schema = None
        self.generations = []

    def initialize(self, config: Dict[str, Any]) -> None:
        self.schema = config.get("schema", {})
        self.initialized = True

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        self.generations.append(task)
        return {
            "framework": "Outlines",
            "schema_type": type(self.schema).__name__,
            "generations_count": len(self.generations),
            "result": task,
            "structured": True
        }

    def shutdown(self) -> None:
        self.initialized = False
        self.schema = None
        self.generations.clear()
