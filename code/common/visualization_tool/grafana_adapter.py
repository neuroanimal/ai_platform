from typing import Any, Dict
from ai_platform.common.visualization_tool.base import VisualizationToolAdapter

class GrafanaAdapter(VisualizationToolAdapter):
    def __init__(self):
        self.connected = False

    def connect(self, config: Dict[str, Any]) -> None:
        self.connected = True

    def create_dashboard(self, data: Any, **kwargs) -> str:
        if not self.connected:
            raise RuntimeError("Not connected")
        return "grafana-dashboard-789"

    def disconnect(self) -> None:
        self.connected = False
