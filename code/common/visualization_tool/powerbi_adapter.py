"""Microsoft Power BI adapter (Power BI REST API, push datasets).

``create_dashboard(data, title=...)``:

1. creates a *push dataset* with one table ``data`` (columns x, y, series),
2. pushes the chart rows (visualization data model) into it,
3. creates an (empty) dashboard with the same title,

and returns the dashboard's ``webUrl``. Power BI has no API to lay out
visuals from scratch - tiles are pinned from reports built on the dataset in
the Power BI service - so the dataset is the reusable output here.

Configuration: ``access_token`` / ``access_token_env`` (Azure AD token for
``https://analysis.windows.net/powerbi/api``, default env POWERBI_TOKEN),
``group_id`` (workspace; default "My workspace"), ``url`` (default
https://api.powerbi.com/v1.0/myorg).

Not verified against the Power BI service here; unit tests use a fake
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

_BATCH = 10000  # Power BI accepts up to 10,000 rows per push request


class PowerBIAdapter(DashboardToolBase):
    """Push datasets and dashboards in Power BI."""

    TOOL = "powerbi"
    DEFAULT_URL = "https://api.powerbi.com/v1.0/myorg"

    def __init__(self):
        super().__init__()
        self.prefix = ""

    def _auth_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        token = secret(config, "access_token", "access_token_env", "POWERBI_TOKEN")
        if not token:
            raise DashboardToolError("powerbi: access token missing (POWERBI_TOKEN)")
        self.prefix = f"/groups/{config['group_id']}" if config.get("group_id") else ""
        return {"Authorization": f"Bearer {token}"}

    def create_dashboard(self, data: Any, **kwargs) -> str:
        """Create dataset, push rows, create dashboard; return its webUrl."""
        self._require()
        try:
            chart = normalize(data, kwargs.get("plot_type", "line"))
        except VisualizationError as exc:
            raise DashboardToolError(str(exc)) from exc
        title = kwargs.get("title", "AI Platform dashboard")
        dataset = self._call("POST", f"{self.prefix}/datasets?defaultRetentionPolicy=basicFIFO", {
            "name": title, "defaultMode": "Push",
            "tables": [{"name": "data", "columns": [
                {"name": "x", "dataType": "string"},
                {"name": "y", "dataType": "Double"},
                {"name": "series", "dataType": "string"}]}]})
        rows = [{"x": str(r["x"]), "y": float(r["y"]), "series": r["series"]}
                for r in chart.records()]
        for start in range(0, len(rows), _BATCH):
            self._call("POST", f"{self.prefix}/datasets/{dataset['id']}/tables/data/rows",
                       {"rows": rows[start:start + _BATCH]})
        dashboard = self._call("POST", f"{self.prefix}/dashboards", {"name": title})
        return dashboard.get("webUrl") or f"dashboard:{dashboard.get('id')}"
