from typing import Any, Dict
from ai_platform.common.prompt.base import PromptAdapter

class PriomptAdapter(PromptAdapter):
    def __init__(self):
        self.initialized = False
        self.priority_queue = []
        self.token_budget = 0

    def initialize(self, config: Dict[str, Any]) -> None:
        self.token_budget = config.get("token_budget", 4096)
        self.initialized = True

    def render(self, template: str, variables: Dict[str, Any]) -> str:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        priority = variables.get("priority", 1)
        self.priority_queue.append({"template": template, "priority": priority})
        return f"Priompt[budget={self.token_budget}]: {template[:30]}... (priority={priority})"

    def shutdown(self) -> None:
        self.initialized = False
        self.priority_queue.clear()
        self.token_budget = 0
