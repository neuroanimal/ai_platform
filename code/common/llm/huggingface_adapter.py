from typing import Any, Dict, List
from ai_platform.common.llm.base import LLMAdapter

class HuggingFaceAdapter(LLMAdapter):
    def __init__(self):
        self.initialized = False

    def initialize(self, config: Dict[str, Any]) -> None:
        self.model = config.get("model", "meta-llama")
        self.initialized = True

    def generate(self, prompt: str, **kwargs) -> str:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        return f"HuggingFace({self.model}): {prompt[:20]}..."

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        return f"HuggingFace({self.model}): chat response"

    def shutdown(self) -> None:
        self.initialized = False
