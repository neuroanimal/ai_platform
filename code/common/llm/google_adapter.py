from typing import Any, Dict, List
from code.common.llm.base import LLMAdapter

class GoogleAdapter(LLMAdapter):
    def __init__(self):
        self.initialized = False

    def initialize(self, config: Dict[str, Any]) -> None:
        self.model = config.get("model", "gemini-pro")
        self.initialized = True

    def generate(self, prompt: str, **kwargs) -> str:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        return f"Google({self.model}): {prompt[:20]}..."

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        return f"Google({self.model}): chat response"

    def shutdown(self) -> None:
        self.initialized = False
