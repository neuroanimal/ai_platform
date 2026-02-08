from typing import Any, Dict, List
from ai_platform.common.rag.base import RAGAdapter

class CanopyAdapter(RAGAdapter):
    def __init__(self):
        self.initialized = False

    def initialize(self, config: Dict[str, Any]) -> None:
        self.initialized = True

    def ingest(self, documents: List[Dict[str, Any]]) -> None:
        if not self.initialized:
            raise RuntimeError("Not initialized")

    def query(self, question: str, **kwargs) -> Dict[str, Any]:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        return {"stack": "Canopy", "answer": f"Response to: {question[:30]}...", "sources": []}

    def shutdown(self) -> None:
        self.initialized = False
