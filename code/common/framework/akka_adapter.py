"""Akka adapter: calls an Akka service over HTTP.

Akka runs on the JVM (Scala/Java), so Python cannot host actors; what a
Python adapter can do for real is call an Akka service - Akka SDK
components and Akka HTTP routes are exposed as HTTP endpoints.

Configuration: ``url`` (service base URL), ``api_key`` / ``api_key_env``
(optional Bearer token), ``timeout`` (default 60).

``execute({"input": body, "path": "/greetings/alice", "method": "POST"})``
sends ``input`` as JSON (``method`` defaults to POST, or GET when ``input``
is None) and returns the decoded JSON answer as ``output``.

Not verified against a running Akka service here; unit tests use a fake
server. Previously a stub echoing the task; the class name and the
FrameworkAdapter methods are unchanged.
"""

import os
from typing import Any, Dict

from ai_platform.common.framework.framework_support import FrameworkBase, FrameworkError
from ai_platform.common.util.http_json_client import HttpJsonClient, HttpJsonError


class AkkaAdapter(FrameworkBase):
    """HTTP client of an Akka service."""

    FRAMEWORK = "Akka"

    def __init__(self):
        super().__init__()
        self._client = None

    def _setup(self, config: Dict[str, Any]) -> None:
        url = self._needs("url", "base URL of the Akka service")
        key = config.get("api_key") or os.environ.get(config.get("api_key_env") or "")
        self._client = HttpJsonClient(url, timeout=float(config.get("timeout", 60)),
                                      headers={"Authorization": f"Bearer {key}"} if key else {})

    def _run(self, task: Dict[str, Any]):
        if "path" not in task:
            raise FrameworkError("Akka task needs 'path' (endpoint of the service)")
        body = task.get("input")
        method = task.get("method", "GET" if body is None else "POST").upper()
        try:
            data = self._client.request(method, task["path"], body).data
        except HttpJsonError as exc:
            raise FrameworkError(f"akka: {exc}") from exc
        return data, data
