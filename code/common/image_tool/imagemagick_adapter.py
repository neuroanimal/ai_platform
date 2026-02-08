from typing import Any, Dict
from ai_platform.common.image_tool.base import ImageToolAdapter

class ImageMagickAdapter(ImageToolAdapter):
    def __init__(self):
        self.connected = False

    def connect(self, config: Dict[str, Any]) -> None:
        self.connected = True

    def process(self, input_path: str, operations: Dict[str, Any]) -> str:
        if not self.connected:
            raise RuntimeError("Not connected")
        return f"imagemagick-processed-{input_path}"

    def disconnect(self) -> None:
        self.connected = False
