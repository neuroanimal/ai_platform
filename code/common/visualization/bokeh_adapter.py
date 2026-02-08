from typing import Any, Dict
from ai_platform.common.visualization.base import VisualizationAdapter

class BokehAdapter(VisualizationAdapter):
    def __init__(self):
        self.initialized = False
        self.figure = None

    def initialize(self, config: Dict[str, Any]) -> None:
        self.initialized = True

    def plot(self, data: Any, plot_type: str, **kwargs) -> Any:
        if not self.initialized:
            raise RuntimeError("Not initialized")
        self.figure = {"library": "Bokeh", "type": plot_type, "data": data}
        return self.figure

    def save(self, output_path: str) -> None:
        if not self.initialized:
            raise RuntimeError("Not initialized")

    def shutdown(self) -> None:
        self.initialized = False
        self.figure = None
