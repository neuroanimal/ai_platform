"""
Shared base of the dashboard tool adapters (Grafana, Metabase, Superset,
Power BI).

These are servers with REST APIs; each adapter creates a real dashboard
through its tool's API and returns the dashboard URL. What ``data`` means
depends on what the tool can hold - see each adapter. Every adapter
accepts ``title`` as a keyword of ``create_dashboard``.

Configuration keys common to all: ``url`` (server base URL), ``timeout``
(default 60). Credentials: each adapter documents its own; secrets are
read from environment variables by name where possible.
"""

import os
from typing import Any, Dict, Optional

from ai_platform.common.util.http_json_client import HttpJsonClient, HttpJsonError
from ai_platform.common.visualization_tool.base import VisualizationToolAdapter


class DashboardToolError(Exception):
    """Dashboard tool misuse or API failure."""


def secret(config: Dict[str, Any], key: str, env_key: str, default_env: str) -> Optional[str]:
    """config[key], else the environment variable named by config[env_key] or default_env."""
    return config.get(key) or os.environ.get(config.get(env_key) or default_env)


class DashboardToolBase(VisualizationToolAdapter):
    """REST client lifecycle shared by the dashboard adapters."""

    TOOL = "dashboard"
    DEFAULT_URL = ""

    def __init__(self):
        self.connected = False
        self.base_url = ""
        self._client: Optional[HttpJsonClient] = None

    def connect(self, config: Dict[str, Any]) -> None:
        """Build the client, then let the tool authenticate."""
        config = dict(config or {})
        self.base_url = (config.get("url") or self.DEFAULT_URL).rstrip("/")
        if not self.base_url:
            raise DashboardToolError(f"{self.TOOL}: 'url' is required")
        self._client = HttpJsonClient(self.base_url, timeout=float(config.get("timeout", 60)),
                                      headers=self._auth_headers(config),
                                      cookies=self.USES_COOKIES)
        self._login(config)
        self.connected = True

    def disconnect(self) -> None:
        """Drop the client (and its session)."""
        self._client = None
        self.connected = False

    # -- hooks ----------------------------------------------------------------

    USES_COOKIES = False

    def _auth_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Static auth headers (default: none)."""
        del config
        return {}

    def _login(self, config: Dict[str, Any]) -> None:
        """Interactive login step (default: none)."""

    # -- helpers ----------------------------------------------------------------

    def _call(self, method: str, path: str, payload: Any = None) -> Any:
        if not self.connected and self._client is None:
            raise DashboardToolError(f"{self.TOOL} adapter is not connected")
        try:
            return self._client.request(method, path, payload).data
        except HttpJsonError as exc:
            raise DashboardToolError(f"{self.TOOL}: {exc}") from exc

    def _require(self) -> None:
        if not self.connected:
            raise DashboardToolError(f"{self.TOOL} adapter is not connected")
