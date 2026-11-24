"""
HTTP API and static file server of the browser chat (Python standard library only).

    python -m ai_platform.backend.ui_layer.web.chat_server            # http://127.0.0.1:8765
    python -m ai_platform.backend.ui_layer.web.chat_server --documents ~/notes
    python -m ai_platform.backend.ui_layer.web.chat_server --documents demo:bilingual_qa

Routes:

    GET  /                  the chat page (code/frontend/channel/web/chat/index.html)
    GET  /static/<file>     its script and style sheet (only files of that directory)
    GET  /api/models        chat models of the reachable local servers
    GET  /api/status        providers and the document corpus
    POST /api/chat          JSON request -> Server-Sent Events (sources, delta, trace,
                            finish, done / error), see chat_service.ChatService.answer

SECURITY: there is NO authentication. The server binds to 127.0.0.1 and
refuses another address unless ``--allow-remote`` is given - then anybody who
can reach the port can use the local models and read the document corpus
through the answers. Requests whose Host header is not the bound address (DNS
rebinding) or whose Origin is a different site are rejected, ``/api/chat``
accepts only ``Content-Type: application/json`` (a plain cross-site form
cannot send it) and bodies up to ``MAX_BODY_BYTES``. The document directory is
fixed at start; a request cannot name a path.
"""

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlsplit

from ai_platform.backend.service_layer.macro.chat.chat_service import (
    DEFAULT_MIN_SCORE,
    DEMO_CORPUS,
    ChatService,
)

#: code/frontend/channel/web/chat, located from this file (code/backend/ui_layer/web/).
DEFAULT_STATIC_DIR = Path(__file__).resolve().parents[3] / "frontend" / "channel" / "web" / "chat"
STATIC_TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
                ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml"}
MAX_BODY_BYTES = 1_000_000
LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")


class ChatHandler(BaseHTTPRequestHandler):
    """Routes of the chat API; ``make_handler`` binds the service and the directories."""

    server_version = "ai_platform-chat/1"
    service: ChatService
    static_dir: Path
    allowed_hosts: frozenset = frozenset(LOCAL_HOSTS)

    def log_message(self, format, *args):  # pylint: disable=redefined-builtin
        """Short access log on stderr."""
        sys.stderr.write(f"{self.address_string()} {format % args}\n")

    # -- checks ----------------------------------------------------------

    def _host_ok(self) -> bool:
        host = urlsplit(f"//{self.headers.get('Host', '')}").hostname or ""
        if host not in self.allowed_hosts:
            return False
        origin = self.headers.get("Origin")
        return origin is None or (urlsplit(origin).hostname or "") in self.allowed_hosts

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; style-src 'self'; script-src 'self'")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, data: Any) -> None:
        self._send(status, json.dumps(data, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    # -- routes ----------------------------------------------------------

    def do_GET(self):  # pylint: disable=invalid-name
        """Page, static files, models, status."""
        if not self._host_ok():
            self._json(403, {"error": "host or origin not allowed"})
            return
        path = urlsplit(self.path).path
        if path == "/api/models":
            self._json(200, {"models": self.service.list_models(max_age=0)})
        elif path == "/api/status":
            self._json(200, self.service.status())
        elif path in ("/", "/index.html"):
            self._static("index.html")
        elif path.startswith("/static/"):
            self._static(path[len("/static/"):])
        else:
            self._json(404, {"error": "not found"})

    def _static(self, name: str) -> None:
        target = (self.static_dir / name).resolve()
        if target.parent != self.static_dir or target.suffix not in STATIC_TYPES \
                or not target.is_file():
            self._json(404, {"error": "not found"})
            return
        self._send(200, target.read_bytes(), STATIC_TYPES[target.suffix])

    def do_POST(self):  # pylint: disable=invalid-name
        """``/api/chat``: answer as Server-Sent Events."""
        if not self._host_ok():
            self._json(403, {"error": "host or origin not allowed"})
            return
        if urlsplit(self.path).path != "/api/chat":
            self._json(404, {"error": "not found"})
            return
        request = self._read_json()
        if request is not None:
            self._stream(request)

    def _read_json(self) -> Optional[dict]:
        """The JSON object of the body, or None after sending the error response."""
        if not self.headers.get("Content-Type", "").startswith("application/json"):
            self._json(415, {"error": "Content-Type must be application/json"})
            return None
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BODY_BYTES:
            self._json(413, {"error": f"body must be 1..{MAX_BODY_BYTES} bytes"})
            return None
        try:
            request = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            request = None
        if not isinstance(request, dict):
            self._json(400, {"error": "body must be a JSON object"})
            return None
        return request

    def _stream(self, request: dict) -> None:
        """Answer events as Server-Sent Events, one frame per event."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        # BaseHTTPRequestHandler attribute: no keep-alive after a stream of unknown length.
        self.close_connection = True  # pylint: disable=attribute-defined-outside-init
        try:
            for event in self.service.answer(request):
                data = json.dumps(event, ensure_ascii=False)
                self.wfile.write(f"event: {event['type']}\ndata: {data}\n\n".encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass  # the browser stopped the answer (Stop button or closed tab)


def make_handler(service: ChatService, static_dir: Path, allowed_hosts):
    """Request handler class bound to ``service`` and ``static_dir``."""
    return type("BoundChatHandler", (ChatHandler,),
                {"service": service, "static_dir": static_dir.resolve(),
                 "allowed_hosts": frozenset(allowed_hosts)})


def create_server(service: ChatService, host: str = "127.0.0.1", port: int = 8765,
                  static_dir: Path = DEFAULT_STATIC_DIR) -> ThreadingHTTPServer:
    """Server bound to ``host:port`` (port 0 = any free port)."""
    allowed = set(LOCAL_HOSTS) | {host}
    server = ThreadingHTTPServer((host, port), make_handler(service, static_dir, allowed))
    server.daemon_threads = True
    return server


def build_parser() -> argparse.ArgumentParser:
    """Command line options."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", maxsplit=1)[0])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--allow-remote", action="store_true",
                        help="allow a non-local --host (there is no authentication!)")
    parser.add_argument("--documents", default=DEMO_CORPUS,
                        help=f"directory of .txt/.md files, or {DEMO_CORPUS} (default), "
                             "or 'none'")
    parser.add_argument("--embedder", default="ollama:bge-m3",
                        help="embedder spec for the documents (see create_embedder)")
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--min-score", type=float, default=DEFAULT_MIN_SCORE,
                        help="drop passages scoring below this (default calibrated for "
                             "ollama:bge-m3; use a negative value to keep all)")
    parser.add_argument("--static-dir", default=str(DEFAULT_STATIC_DIR))
    return parser


def main(argv: Optional[list] = None) -> int:
    """Run the chat server until Ctrl-C."""
    args = build_parser().parse_args(argv)
    if args.host not in LOCAL_HOSTS and not args.allow_remote:
        print(f"refusing to listen on {args.host}: the chat has no authentication; "
              "use --allow-remote only on a trusted network", file=sys.stderr)
        return 2
    documents = None if args.documents == "none" else args.documents
    service = ChatService(documents=documents, embedder=args.embedder, top_k=args.top_k,
                          min_score=args.min_score if args.min_score >= 0 else None)
    server = create_server(service, args.host, args.port, Path(args.static_dir))
    host, port = server.server_address[:2]
    print(f"chat on http://{host}:{port}/  (documents: {documents or 'none'}; Ctrl-C to stop)",
          file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        service.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
