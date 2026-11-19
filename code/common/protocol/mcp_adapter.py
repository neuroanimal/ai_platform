"""Model Context Protocol (MCP) client adapter (official ``mcp`` SDK, 2.x).

Connects to one MCP server and exposes its requests through the
synchronous ProtocolAdapter interface. The SDK is asynchronous, so the
session lives on a private event loop in a background thread for the whole
connect()..disconnect() lifetime.

Configuration for ``connect()`` (one transport):

    command, args, env, cwd   start a local server and talk over stdio
    url                       streamable HTTP endpoint, e.g. "http://127.0.0.1:8000/mcp"
    timeout                   seconds per request, default 60

``send(message)`` - ``message = {"method": ..., "params": {...}}``:

    tools/list        -> {"tools": [...]}
    tools/call        params {"name", "arguments"} -> {"content": [...], "isError": bool, ...}
    resources/list    -> {"resources": [...]}
    resources/read    params {"uri"}
    prompts/list      -> {"prompts": [...]}
    prompts/get       params {"name", "arguments"}
    ping

Results are the SDK's result models dumped to JSON-compatible dicts.
``receive()`` returns the oldest queued server notification/log message
(``{}`` when none).

Previously a stub returning fabricated results; the class name and the
ProtocolAdapter methods are unchanged.
"""

import asyncio
import contextlib
import queue
import threading
from typing import Any, Dict, Optional

from ai_platform.common.protocol.base import ProtocolAdapter


class ProtocolError(Exception):
    """Protocol adapter misuse or failure."""


class MCPAdapter(ProtocolAdapter):  # pylint: disable=too-many-instance-attributes
    """Synchronous facade over an MCP ClientSession."""

    def __init__(self):
        self.connected = False
        self.timeout = 60.0
        self.server_info: Dict[str, Any] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._stack: Optional[contextlib.AsyncExitStack] = None
        self._session = None
        self._inbox: "queue.Queue[Dict[str, Any]]" = queue.Queue()

    # -- ProtocolAdapter -------------------------------------------------

    def connect(self, config: Dict[str, Any]) -> None:
        """Start the transport, initialize the session."""
        try:
            import mcp  # noqa: F401 pylint: disable=import-outside-toplevel,unused-import
        except ImportError as exc:
            raise ProtocolError("MCPAdapter requires: pip install mcp") from exc
        if not config.get("command") and not config.get("url"):
            raise ProtocolError("MCPAdapter needs 'command' (stdio) or 'url' (streamable HTTP)")
        self.timeout = float(config.get("timeout", 60))
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True,
                                        name="mcp-client-loop")
        self._thread.start()
        try:
            self.server_info = self._run(self._open(config))
        except Exception:
            self._stop_loop()
            raise
        self.connected = True

    def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send one request and return its result as a dict."""
        if not self.connected:
            raise ProtocolError("MCPAdapter is not connected")
        method = message.get("method")
        params = message.get("params") or {}
        return self._run(self._request(method, params))

    def receive(self) -> Dict[str, Any]:
        """Oldest queued server notification, or {} when none arrived."""
        try:
            return self._inbox.get_nowait()
        except queue.Empty:
            return {}

    def disconnect(self) -> None:
        """Close the session and the transport (terminates a stdio server)."""
        if self._loop is not None and self._stack is not None:
            with contextlib.suppress(Exception):
                self._run(self._stack.aclose())
        self._stop_loop()
        self._session = None
        self.connected = False

    # -- async internals ---------------------------------------------------

    async def _open(self, config: Dict[str, Any]) -> Dict[str, Any]:
        from mcp import ClientSession  # pylint: disable=import-outside-toplevel

        self._stack = contextlib.AsyncExitStack()
        if config.get("command"):
            from mcp import StdioServerParameters  # pylint: disable=import-outside-toplevel
            from mcp.client.stdio import stdio_client  # pylint: disable=import-outside-toplevel
            params = StdioServerParameters(command=config["command"],
                                           args=list(config.get("args", [])),
                                           env=config.get("env"), cwd=config.get("cwd"))
            streams = await self._stack.enter_async_context(stdio_client(params))
        else:
            from mcp.client.streamable_http import (  # pylint: disable=import-outside-toplevel
                streamable_http_client,
            )
            streams = await self._stack.enter_async_context(streamable_http_client(config["url"]))
        read, write = streams[0], streams[1]

        async def on_message(message):
            self._inbox.put({"type": type(message).__name__, "message": _dump(message)})

        self._session = await self._stack.enter_async_context(
            ClientSession(read, write, read_timeout_seconds=self.timeout,
                          message_handler=on_message))
        return _dump(await self._session.initialize())

    async def _request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        session = self._session
        handlers = {
            "tools/list": session.list_tools,
            "tools/call": lambda: session.call_tool(params["name"], params.get("arguments") or {}),
            "resources/list": session.list_resources,
            "resources/read": lambda: session.read_resource(params["uri"]),
            "prompts/list": session.list_prompts,
            "prompts/get": lambda: session.get_prompt(params["name"], params.get("arguments")),
            "ping": session.send_ping,
        }
        if method not in handlers:
            raise ProtocolError(f"unsupported MCP method {method!r}; supported: {sorted(handlers)}")
        try:
            return _dump(await handlers[method]())
        except KeyError as exc:
            raise ProtocolError(f"{method}: missing parameter {exc}") from exc

    def _run(self, coroutine):
        future = asyncio.run_coroutine_threadsafe(coroutine, self._loop)
        try:
            return future.result(timeout=self.timeout + 5)
        except TimeoutError as exc:
            future.cancel()
            raise ProtocolError(f"MCP request timed out after {self.timeout:.0f} s") from exc

    def _stop_loop(self) -> None:
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
            if self._thread is not None:
                self._thread.join(timeout=5)
            self._loop.close()
        self._loop = self._thread = self._stack = None


def _dump(value: Any) -> Dict[str, Any]:
    """Pydantic model (or anything) -> JSON-compatible dict."""
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True, exclude_none=True)
    if isinstance(value, dict):
        return value
    return {"value": value}
