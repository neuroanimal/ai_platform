from typing import Any, Dict
from code.common.prompt.base import PromptAdapter

class LMQLAdapter(PromptAdapter):
    def __init__(self):
        self.initialized = False
        self.queries = []
        self.constraints = {}

    def initialize(self, config: Dict[str, Any]) -> None:
        self.constraints = config.get("constraints", {})
        self.initialized = True

    def render(self, template: str, variables: Dict[str, Any]) -> str:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        self.queries.append({"template": template, "variables": variables})
        return f"LMQL[query_{len(self.queries)}]: {template[:30]}... constrained by {len(self.constraints)} rules"

    def shutdown(self) -> None:
        self.initialized = False
        self.queries.clear()
        self.constraints = {}
