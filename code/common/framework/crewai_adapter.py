from typing import Any, Dict
from ai_platform.common.framework.base import FrameworkAdapter

class CrewAIAdapter(FrameworkAdapter):
    """CrewAI framework adapter."""

    def __init__(self):
        self.initialized = False
        self.crew = None

    def initialize(self, config: Dict[str, Any]) -> None:
        self.crew = config.get("crew_name", "default")
        self.initialized = True

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        return {"framework": "CrewAI", "crew": self.crew, "result": task}

    def shutdown(self) -> None:
        self.initialized = False
        self.crew = None
