from typing import Any, Dict
from code.common.prompt.base import PromptAdapter

class PromptLayerAdapter(PromptAdapter):
    def __init__(self):
        self.initialized = False
        self.api_key = None
        self.logged_prompts = []

    def initialize(self, config: Dict[str, Any]) -> None:
        self.api_key = config.get("api_key", "mock_key")
        self.initialized = True

    def render(self, template: str, variables: Dict[str, Any]) -> str:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        self.logged_prompts.append({"template": template, "variables": variables})
        return f"PromptLayer[logged={len(self.logged_prompts)}]: {template[:30]}..."

    def shutdown(self) -> None:
        self.initialized = False
        self.api_key = None
        self.logged_prompts.clear()
