"""
Minimal JSON-over-HTTP client built on the standard library.

Used by adapters that talk to REST services (OpenAI-compatible LLM servers,
Ollama, vector databases with a REST API). It deliberately has no third-party
dependency so that ``code/common`` stays free of runtime frameworks, as
required by ``doc/arch/DEPENDENCY_RULES.md``.

Secrets: headers are never included in exception messages or ``repr``.
"""

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional


class HttpJsonError(Exception):
    """Base error of the JSON HTTP client."""


class HttpConnectionError(HttpJsonError):
    """The server could not be reached (refused, DNS, timeout)."""


class HttpStatusError(HttpJsonError):
    """The server answered with a non-2xx status code."""

    def __init__(self, url: str, status: int, body: str) -> None:
        # Body is truncated: servers may echo large payloads back.
        super().__init__(f"HTTP {status} from {url}: {body[:500]}")
        self.url = url
        self.status = status
        self.body = body


class HttpDecodeError(HttpJsonError):
    """The response body is not valid JSON."""


@dataclass
class HttpJsonResponse:
    """Decoded JSON body plus timing of one request."""

    data: Any
    status: int
    elapsed_seconds: float


@dataclass
class HttpJsonClient:
    """Send JSON requests to one base URL.

    ``headers`` may carry an ``Authorization`` header; it is excluded from
    ``repr`` so that it does not leak into logs.
    """

    base_url: str
    timeout: float = 120.0
    headers: Dict[str, str] = field(default_factory=dict, repr=False)

    def url(self, path: str) -> str:
        """Join the base URL and a path without doubling slashes."""
        return self.base_url.rstrip("/") + "/" + path.lstrip("/")

    def get(self, path: str, timeout: Optional[float] = None) -> HttpJsonResponse:
        """GET ``path`` and decode the JSON answer."""
        return self.request("GET", path, None, timeout)

    def post(
        self,
        path: str,
        payload: Mapping[str, Any],
        timeout: Optional[float] = None,
    ) -> HttpJsonResponse:
        """POST ``payload`` as JSON to ``path`` and decode the JSON answer."""
        return self.request("POST", path, payload, timeout)

    def request(
        self,
        method: str,
        path: str,
        payload: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> HttpJsonResponse:
        """Perform one request; raise an ``HttpJsonError`` subclass on failure."""
        url = self.url(path)
        headers = {"Accept": "application/json", **self.headers}
        data = None

        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        start = time.perf_counter()

        try:
            with urllib.request.urlopen(request, timeout=timeout or self.timeout) as response:
                raw = response.read()
                status = response.status
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise HttpStatusError(url, exc.code, body) from exc
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            raise HttpConnectionError(f"Cannot reach {url}: {exc}") from exc

        elapsed = time.perf_counter() - start

        try:
            decoded = json.loads(raw.decode("utf-8")) if raw else None
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HttpDecodeError(f"Invalid JSON from {url}: {raw[:200]!r}") from exc

        return HttpJsonResponse(decoded, status, elapsed)
