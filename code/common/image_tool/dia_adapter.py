from typing import Any, Dict
from code.common.image_tool.base import ImageToolAdapter

class DiaAdapter(ImageToolAdapter):
    def __init__(self):
        self.connected = False

    def connect(self, config: Dict[str, Any]) -> None:
        self.connected = True

    def process(self, input_path: str, operations: Dict[str, Any]) -> str:
        if not self.connected:
            raise RuntimeError("Not connected")
        return f"dia-processed-{input_path}"

    def disconnect(self) -> None:
        self.connected = False
