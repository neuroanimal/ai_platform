from typing import Any, Dict
from ai_platform.common.prompt.base import PromptAdapter

class LangChainPromptAdapter(PromptAdapter):
    def __init__(self):
        self.initialized = False
        self.prompt_templates = {}
        self.render_history = []

    def initialize(self, config: Dict[str, Any]) -> None:
        self.prompt_templates = config.get("templates", {})
        self.initialized = True

    def render(self, template: str, variables: Dict[str, Any]) -> str:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        self.render_history.append({"template": template, "vars": variables})
        return f"LangChainPrompt[{len(self.render_history)}]: {template[:30]}... with {list(variables.keys())}"

    def shutdown(self) -> None:
        self.initialized = False
        self.prompt_templates = {}
        self.render_history.clear()
