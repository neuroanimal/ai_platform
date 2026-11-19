"""Agent Communication Protocol (ACP) client adapter (REST).

ACP (originally from IBM's BeeAI project) exposes agents over plain REST:

    GET  /agents              list agents
    POST /runs                start a run: {"agent_name", "input": [Message], "mode"}
    GET  /runs/<run_id>       poll a run

To the best of the author's knowledge ACP development has since been folded
into A2A (see ``A2AAdapter``); this adapter targets the ACP REST API as
published and is not verified against a live ACP server.

Configuration:

    url                     server base URL
    agent                   default agent name for send()
    api_key / api_key_env   optional Bearer token
    timeout                 seconds, default 120

``send({"text": ..., "agent"?: ..., "mode"?: "sync"|"async"})`` starts a run
and returns it; in sync mode the answer text is also under ``"text"``.
``receive()`` polls the last run that was not yet finished.

Previously a stub returning fabricated results; the class name and the
ProtocolAdapter methods are unchanged.
"""

import os
from typing import Any, Dict, List, Optional

from ai_platform.common.protocol.base import ProtocolAdapter
from ai_platform.common.protocol.mcp_adapter import ProtocolError
from ai_platform.common.util.http_json_client import HttpJsonClient, HttpJsonError

_FINISHED = {"completed", "failed", "cancelled", "canceled"}


def output_text(run: Dict[str, Any]) -> str:
    """Concatenate the text parts of a run's output messages."""
    texts = []
    for message in run.get("output") or []:
        for part in message.get("parts") or []:
            if str(part.get("content_type", "text/plain")).startswith("text/"):
                texts.append(str(part.get("content", "")))
    return "".join(texts)


class ACPAdapter(ProtocolAdapter):
    """Client of an ACP server."""

    def __init__(self):
        self.connected = False
        self.agents: List[Dict[str, Any]] = []
        self.default_agent: Optional[str] = None
        self._client: Optional[HttpJsonClient] = None
        self._pending_run: Optional[str] = None

    def connect(self, config: Dict[str, Any]) -> None:
        """List the server's agents (also checks reachability)."""
        if not config.get("url"):
            raise ProtocolError("ACPAdapter needs 'url'")
        key = config.get("api_key") or os.environ.get(config.get("api_key_env") or "")
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        self._client = HttpJsonClient(config["url"], timeout=float(config.get("timeout", 120)),
                                      headers=headers)
        self.agents = self._call("GET", "/agents").get("agents", [])
        self.default_agent = config.get("agent") or (
            self.agents[0]["name"] if len(self.agents) == 1 else None)
        self.connected = True

    def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Start a run with one user text message."""
        self._require()
        agent = message.get("agent") or self.default_agent
        if not agent:
            names = [a.get("name") for a in self.agents]
            raise ProtocolError(f"no agent given; available: {names}")
        run = self._call("POST", "/runs", {
            "agent_name": agent,
            "mode": message.get("mode", "sync"),
            "input": [{"role": "user", "parts": [
                {"content": str(message.get("text", "")), "content_type": "text/plain"}]}],
        })
        return self._track(run)

    def receive(self) -> Dict[str, Any]:
        """Poll the last unfinished run; {} when none is pending."""
        self._require()
        if not self._pending_run:
            return {}
        return self._track(self._call("GET", f"/runs/{self._pending_run}"))

    def disconnect(self) -> None:
        """Drop the client."""
        self._client = None
        self._pending_run = None
        self.connected = False

    def _track(self, run: Dict[str, Any]) -> Dict[str, Any]:
        finished = run.get("status") in _FINISHED
        self._pending_run = None if finished else run.get("run_id")
        return {**run, "text": output_text(run)}

    def _call(self, method: str, path: str, payload: Any = None) -> Dict[str, Any]:
        try:
            return self._client.request(method, path, payload).data or {}
        except HttpJsonError as exc:
            raise ProtocolError(f"acp: {exc}") from exc

    def _require(self) -> None:
        if not self.connected or self._client is None:
            raise ProtocolError("ACPAdapter is not connected")
