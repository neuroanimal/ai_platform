from typing import Any, Dict
from ai_platform.common.scientific_tool.base import ScientificToolAdapter

class OctaveAdapter(ScientificToolAdapter):
    def __init__(self):
        self.connected = False

    def connect(self, config: Dict[str, Any]) -> None:
        self.connected = True

    def execute(self, script: str, **kwargs) -> Any:
        if not self.connected:
            raise RuntimeError("Not connected")
        return {"tool": "Octave", "result": "computed"}

    def disconnect(self) -> None:
        self.connected = False
