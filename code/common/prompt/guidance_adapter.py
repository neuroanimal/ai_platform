from typing import Any, Dict
from code.common.prompt.base import PromptAdapter

class GuidanceAdapter(PromptAdapter):
    def __init__(self):
        self.initialized = False
        self.templates = {}
        self.render_count = 0

    def initialize(self, config: Dict[str, Any]) -> None:
        self.templates = config.get("templates", {})
        self.initialized = True

    def render(self, template: str, variables: Dict[str, Any]) -> str:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        self.render_count += 1
        return f"Guidance[{self.render_count}]: {template[:30]}... with {len(variables)} vars"

    def shutdown(self) -> None:
        self.initialized = False
        self.templates = {}
        self.render_count = 0
