from typing import Any, Dict, List
from ai_platform.common.llm.base import LLMAdapter

class QwenAdapter(LLMAdapter):
    def __init__(self):
        self.initialized = False

    def initialize(self, config: Dict[str, Any]) -> None:
        self.model = config.get("model", "qwen-max")
        self.initialized = True

    def generate(self, prompt: str, **kwargs) -> str:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        return f"Qwen({self.model}): {prompt[:20]}..."

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        return f"Qwen({self.model}): chat response"

    def shutdown(self) -> None:
        self.initialized = False
