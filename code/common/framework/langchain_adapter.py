from typing import Any, Dict
from code.common.framework.base import FrameworkAdapter

class LangChainAdapter(FrameworkAdapter):
    """LangChain framework adapter."""

    def __init__(self):
        self.initialized = False
        self.chain = None

    def initialize(self, config: Dict[str, Any]) -> None:
        self.chain = config.get("chain_type", "default")
        self.initialized = True

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        return {"framework": "LangChain", "chain": self.chain, "result": task}

    def shutdown(self) -> None:
        self.initialized = False
        self.chain = None
