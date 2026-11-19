"""Apache Superset adapter (REST API, ``/api/v1``).

Logs in (``/api/v1/security/login``, JWT), fetches a CSRF token
(``/api/v1/security/csrf_token/``, session cookie kept) and creates a
dashboard with ``POST /api/v1/dashboard/``. ``data`` may list existing
chart ids to attach: ``{"chart_ids": [3, 7]}`` (each chart is updated with
``PUT /api/v1/chart/<id>`` to include the new dashboard). Returns the
dashboard URL.

Superset charts are built on datasets in connected databases, so this
adapter organizes existing charts rather than uploading raw data.

Configuration: ``url`` (default http://127.0.0.1:8088), ``username``,
``password`` / ``password_env`` (default env SUPERSET_PASSWORD),
``provider`` ("db" default, or "ldap").

Not verified against a running Superset here; unit tests use a fake
server. Previously a stub returning a fake URL; the class name and the
VisualizationToolAdapter methods are unchanged.
"""

from typing import Any, Dict

from ai_platform.common.visualization_tool.dashboard_support import (
    DashboardToolBase,
    DashboardToolError,
    secret,
)


class SupersetAdapter(DashboardToolBase):
    """Dashboards in Apache Superset."""

    TOOL = "superset"
    DEFAULT_URL = "http://127.0.0.1:8088"
    USES_COOKIES = True

    def _login(self, config: Dict[str, Any]) -> None:
        password = secret(config, "password", "password_env", "SUPERSET_PASSWORD")
        if not config.get("username") or not password:
            raise DashboardToolError("superset: username and password (SUPERSET_PASSWORD) needed")
        token = self._call("POST", "/api/v1/security/login", {
            "username": config["username"], "password": password,
            "provider": config.get("provider", "db"), "refresh": True})["access_token"]
        self._client.headers["Authorization"] = f"Bearer {token}"
        csrf = self._call("GET", "/api/v1/security/csrf_token/")["result"]
        self._client.headers["X-CSRFToken"] = csrf
        self._client.headers["Referer"] = self.base_url

    def create_dashboard(self, data: Any, **kwargs) -> str:
        """Create the dashboard and attach existing charts; return the URL."""
        self._require()
        created = self._call("POST", "/api/v1/dashboard/", {
            "dashboard_title": kwargs.get("title", "AI Platform dashboard"),
            "published": bool(kwargs.get("published", False))})
        dashboard_id = created["id"]
        for chart_id in (data or {}).get("chart_ids", []):
            self._call("PUT", f"/api/v1/chart/{int(chart_id)}", {"dashboards": [dashboard_id]})
        return f"{self.base_url}/superset/dashboard/{dashboard_id}/"
