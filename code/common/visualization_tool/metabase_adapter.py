"""Metabase adapter (REST API).

``create_dashboard(data, title=...)`` creates a dashboard and, for each
question in ``data["questions"]``, a native-SQL card placed on it::

    {"questions": [{"name": "Latency", "sql": "SELECT ...", "database_id": 1,
                    "display": "line"}]}

Returns the dashboard URL (``<url>/dashboard/<id>``). Metabase shows data
from its connected databases, so questions are SQL against one of them.

Configuration: ``url`` (default http://127.0.0.1:3000), and either
``api_key`` / ``api_key_env`` (Metabase API key, default env
METABASE_API_KEY, sent as ``x-api-key``) or ``username`` + ``password``
(session login, ``X-Metabase-Session``).

Targets the dashboard API of Metabase 0.47+ (``dashcards`` in
``PUT /api/dashboard/:id``). Not verified against a running Metabase here;
unit tests use a fake server. Previously a stub returning a fake URL; the
class name and the VisualizationToolAdapter methods are unchanged.
"""

from typing import Any, Dict

from ai_platform.common.visualization_tool.dashboard_support import (
    DashboardToolBase,
    DashboardToolError,
    secret,
)


class MetabaseAdapter(DashboardToolBase):
    """Dashboards in Metabase."""

    TOOL = "metabase"
    DEFAULT_URL = "http://127.0.0.1:3000"

    def _auth_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        key = secret(config, "api_key", "api_key_env", "METABASE_API_KEY")
        return {"x-api-key": key} if key else {}

    def _login(self, config: Dict[str, Any]) -> None:
        if "x-api-key" in self._client.headers:
            return
        if not config.get("username"):
            raise DashboardToolError(
                "metabase: set api_key (METABASE_API_KEY) or username/password")
        session = self._call("POST", "/api/session", {"username": config["username"],
                                                      "password": config.get("password", "")})
        self._client.headers["X-Metabase-Session"] = session["id"]

    def create_dashboard(self, data: Any, **kwargs) -> str:
        """Create the dashboard and its SQL cards; return the URL."""
        self._require()
        dashboard = self._call("POST", "/api/dashboard", {
            "name": kwargs.get("title", "AI Platform dashboard"),
            "description": kwargs.get("description", "")})
        dashcards = []
        for index, question in enumerate((data or {}).get("questions", [])):
            card = self._call("POST", "/api/card", {
                "name": question["name"],
                "display": question.get("display", "table"),
                "visualization_settings": {},
                "dataset_query": {"type": "native", "database": question["database_id"],
                                  "native": {"query": question["sql"]}}})
            dashcards.append({"id": -(index + 1), "card_id": card["id"],
                              "row": index * 6, "col": 0, "size_x": 12, "size_y": 6})
        if dashcards:
            self._call("PUT", f"/api/dashboard/{dashboard['id']}", {"dashcards": dashcards})
        return f"{self.base_url}/dashboard/{dashboard['id']}"
