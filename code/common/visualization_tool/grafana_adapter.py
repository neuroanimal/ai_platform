"""Grafana adapter (HTTP API, ``POST /api/dashboards/db``).

``create_dashboard(data, title=..., plot_type="line")`` creates or
overwrites a dashboard and returns its URL. ``data`` is either:

- chart data in the visualization data model (``{"x": [...], "series":
  {...}}`` etc.): one panel whose values are embedded with Grafana's
  built-in TestData data source (``csv_content`` scenario), so the
  dashboard shows the data without any external database; or
- ``{"panels": [...]}``: Grafana panel JSON, passed through unchanged.

Configuration: ``url`` (default http://127.0.0.1:3000), ``token`` /
``token_env`` (service account token, default env GRAFANA_TOKEN),
``folder_uid`` (optional).

Not verified against a running Grafana here; unit tests use a fake
server. Previously a stub returning a fake URL; the class name and the
VisualizationToolAdapter methods are unchanged.
"""

from typing import Any, Dict

from ai_platform.common.visualization.chart_data import VisualizationError, normalize
from ai_platform.common.visualization_tool.dashboard_support import (
    DashboardToolBase,
    DashboardToolError,
    secret,
)

_PANEL_TYPES = {"line": "timeseries", "scatter": "xychart", "bar": "barchart", "hist": "histogram"}


def csv_panel(data: Any, plot_type: str, title: str) -> Dict[str, Any]:
    """A panel showing ``data`` through the TestData csv_content scenario."""
    try:
        chart = normalize(data, plot_type)
    except VisualizationError as exc:
        raise DashboardToolError(str(exc)) from exc
    header = ",".join(["x", *chart.series])
    rows = [",".join([str(x), *(str(values[i]) for values in chart.series.values())])
            for i, x in enumerate(chart.x)]
    return {
        "id": 1, "title": title, "type": _PANEL_TYPES[plot_type],
        "gridPos": {"x": 0, "y": 0, "w": 24, "h": 10},
        "datasource": {"type": "grafana-testdata-datasource"},
        "targets": [{"refId": "A", "scenarioId": "csv_content",
                     "csvContent": "\n".join([header, *rows])}],
    }


class GrafanaAdapter(DashboardToolBase):
    """Dashboards in Grafana."""

    TOOL = "grafana"
    DEFAULT_URL = "http://127.0.0.1:3000"

    def __init__(self):
        super().__init__()
        self.folder_uid = None

    def _auth_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        token = secret(config, "token", "token_env", "GRAFANA_TOKEN")
        self.folder_uid = config.get("folder_uid")
        return {"Authorization": f"Bearer {token}"} if token else {}

    def create_dashboard(self, data: Any, **kwargs) -> str:
        """Create/overwrite the dashboard; return its URL."""
        self._require()
        title = kwargs.get("title", "AI Platform dashboard")
        panels = data["panels"] if isinstance(data, dict) and "panels" in data else \
            [csv_panel(data, kwargs.get("plot_type", "line"), title)]
        payload = {"dashboard": {"id": None, "uid": kwargs.get("uid"), "title": title,
                                 "panels": panels, "schemaVersion": 39,
                                 "tags": list(kwargs.get("tags", ["ai_platform"]))},
                   "overwrite": True}
        if self.folder_uid:
            payload["folderUid"] = self.folder_uid
        answer = self._call("POST", "/api/dashboards/db", payload) or {}
        if answer.get("status") != "success":
            raise DashboardToolError(f"grafana: unexpected answer {answer}")
        return self.base_url + answer["url"]
