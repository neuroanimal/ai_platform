"""
Shared base of the low-code workflow platform adapters (n8n, Flowise,
Langflow).

Each adapter deploys a workflow definition in the platform's own JSON
format (exported from its editor) and runs it through the platform's HTTP
API. Results are returned as the platform's JSON answer plus a ``text``
key with the main textual output where one can be identified.

Configuration common to all: ``url`` (server base URL), ``timeout``
(default 120), API key as documented per adapter.
"""

import os
from typing import Any, Dict, Optional

from ai_platform.common.lowcode.base import LowCodeAdapter
from ai_platform.common.util.http_json_client import HttpJsonClient, HttpJsonError


class LowCodeError(Exception):
    """Low-code adapter misuse or API failure."""


class LowCodeBase(LowCodeAdapter):
    """REST client lifecycle shared by the low-code adapters."""

    PLATFORM = "lowcode"
    DEFAULT_URL = ""
    KEY_HEADER = "Authorization"
    KEY_SCHEME = "Bearer "
    KEY_ENV = ""
    KEY_REQUIRED = False

    def __init__(self):
        self.connected = False
        self.base_url = ""
        self._client: Optional[HttpJsonClient] = None

    def connect(self, config: Dict[str, Any]) -> None:
        """Build the HTTP client with the platform's auth header."""
        config = dict(config or {})
        self.base_url = (config.get("url") or self.DEFAULT_URL).rstrip("/")
        key = config.get("api_key") or os.environ.get(config.get("api_key_env") or self.KEY_ENV)
        if self.KEY_REQUIRED and not key:
            raise LowCodeError(f"{self.PLATFORM}: API key missing ({self.KEY_ENV})")
        headers = {self.KEY_HEADER: f"{self.KEY_SCHEME}{key}"} if key else {}
        self._client = HttpJsonClient(self.base_url, timeout=float(config.get("timeout", 120)),
                                      headers=headers)
        self._configure(config)
        self.connected = True

    def disconnect(self) -> None:
        """Drop the client."""
        self._client = None
        self.connected = False

    def _configure(self, config: Dict[str, Any]) -> None:
        """Adapter-specific configuration (default: none)."""

    def _call(self, method: str, path: str, payload: Any = None) -> Any:
        if not self.connected or self._client is None:
            raise LowCodeError(f"{self.PLATFORM} adapter is not connected")
        try:
            return self._client.request(method, path, payload).data
        except HttpJsonError as exc:
            raise LowCodeError(f"{self.PLATFORM}: {exc}") from exc
