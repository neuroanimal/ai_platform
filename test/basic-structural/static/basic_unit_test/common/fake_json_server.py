"""
Shared test helper: an in-process fake HTTP server with scripted JSON answers.

Lets adapter tests exercise the real HTTP path (stdlib urllib, real sockets)
without any model server or network access.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Dict, List, Tuple

# A route returns (status, json_body) for (method, path, parsed_body, headers).
Route = Callable[[str, str, Any, Dict[str, str]], Tuple[int, Any]]


class FakeJsonServer:
    """Context manager running a scripted JSON server on a free local port."""

    def __init__(self, routes: Dict[Tuple[str, str], Any]) -> None:
        # routes: {(method, path): body | (status, body) | callable}
        self.routes = routes
        self.requests: List[Dict[str, Any]] = []
        self._server = None
        self._thread = None

    @property
    def url(self) -> str:
        """Base URL of the running server."""
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    def __enter__(self) -> "FakeJsonServer":
        owner = self

        class Handler(BaseHTTPRequestHandler):
            """Dispatch every request to the scripted routes."""

            def _handle(self, method: str) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                try:
                    body = json.loads(raw) if raw else None
                except ValueError:  # multipart or other non-JSON uploads
                    body = raw
                headers = {k.lower(): v for k, v in self.headers.items()}
                owner.requests.append(
                    {"method": method, "path": self.path, "body": body, "headers": headers}
                )

                route = owner.routes.get((method, self.path))
                if route is None:
                    status, answer = 404, {"error": f"no route {method} {self.path}"}
                elif callable(route):
                    status, answer = route(method, self.path, body, headers)
                elif isinstance(route, tuple):
                    status, answer = route
                else:
                    status, answer = 200, route

                payload = answer if isinstance(answer, bytes) else json.dumps(answer).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_GET(self) -> None:  # noqa: N802 - http.server naming
                """Handle GET."""
                self._handle("GET")

            def do_POST(self) -> None:  # noqa: N802 - http.server naming
                """Handle POST."""
                self._handle("POST")

            def do_PUT(self) -> None:  # noqa: N802 - http.server naming
                """Handle PUT."""
                self._handle("PUT")

            def do_DELETE(self) -> None:  # noqa: N802 - http.server naming
                """Handle DELETE."""
                self._handle("DELETE")

            def log_message(self, *args) -> None:  # silence test output
                """Suppress request logging."""

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self._server.shutdown()
        self._server.server_close()


def openai_chat_answer(text: str, finish_reason: str = "stop", model: str = "m") -> Dict[str, Any]:
    """Build a minimal OpenAI Chat Completions response body."""
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": finish_reason,
            }
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
    }
