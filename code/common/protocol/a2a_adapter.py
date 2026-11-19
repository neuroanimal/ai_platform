"""Agent2Agent (A2A) protocol client adapter (JSON-RPC 2.0 over HTTP).

``connect()`` fetches the remote agent's Agent Card
(``/.well-known/agent-card.json``, falling back to the older
``/.well-known/agent.json``) and uses its ``url`` as the JSON-RPC endpoint.

Configuration:

    url                     agent base URL (where the card is served)
    api_key / api_key_env   optional Bearer token
    headers                 extra HTTP headers
    timeout                 seconds, default 120

``send(message)``:

    {"text": "..."}                       -> message/send with one text part
    {"method": "...", "params": {...}}    -> raw JSON-RPC call (tasks/get, tasks/cancel, ...)

returns the JSON-RPC ``result`` (a Task or a Message). ``receive()`` polls
``tasks/get`` for the last task that was not yet in a terminal state and
returns it (``{}`` when there is nothing to poll).

Not verified against a live A2A agent here; unit tests use a fake server.
Previously a stub returning fabricated results; the class name and the
ProtocolAdapter methods are unchanged.
"""

import itertools
import os
import uuid
from typing import Any, Dict, Optional

from ai_platform.common.protocol.base import ProtocolAdapter
from ai_platform.common.protocol.mcp_adapter import ProtocolError
from ai_platform.common.util.http_json_client import HttpJsonClient, HttpJsonError, HttpStatusError

_TERMINAL = {"completed", "canceled", "failed", "rejected"}
_CARD_PATHS = ("/.well-known/agent-card.json", "/.well-known/agent.json")


class A2AAdapter(ProtocolAdapter):
    """Client of one remote A2A agent."""

    def __init__(self):
        self.connected = False
        self.agent_card: Dict[str, Any] = {}
        self._client: Optional[HttpJsonClient] = None
        self._rpc_path = "/"
        self._ids = itertools.count(1)
        self._pending_task: Optional[str] = None

    def connect(self, config: Dict[str, Any]) -> None:
        """Read the Agent Card and prepare the JSON-RPC endpoint."""
        if not config.get("url"):
            raise ProtocolError("A2AAdapter needs 'url'")
        headers = dict(config.get("headers") or {})
        key = config.get("api_key") or os.environ.get(config.get("api_key_env") or "")
        if key:
            headers["Authorization"] = f"Bearer {key}"
        base = config["url"].rstrip("/")
        self._client = HttpJsonClient(base, timeout=float(config.get("timeout", 120)),
                                      headers=headers)
        self.agent_card = self._card()
        endpoint = (self.agent_card.get("url") or base).rstrip("/")
        if endpoint.startswith(base):
            self._rpc_path = endpoint[len(base):] or "/"
        else:  # the card points to another host: talk to that host directly
            self._client = HttpJsonClient(endpoint, timeout=self._client.timeout, headers=headers)
            self._rpc_path = "/"
        self.connected = True

    def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send a text message or a raw JSON-RPC call; return the result."""
        self._require()
        if "method" in message:
            result = self._rpc(message["method"], message.get("params") or {})
        elif "text" in message:
            result = self._rpc("message/send", {"message": {
                "role": "user", "messageId": str(uuid.uuid4()),
                "parts": [{"kind": "text", "text": str(message["text"])}],
                **({"contextId": message["context_id"]} if message.get("context_id") else {}),
            }})
        else:
            raise ProtocolError("send() needs 'text' or 'method'")
        self._track(result)
        return result

    def receive(self) -> Dict[str, Any]:
        """Poll the last non-terminal task; {} when nothing is pending."""
        self._require()
        if not self._pending_task:
            return {}
        result = self._rpc("tasks/get", {"id": self._pending_task})
        self._track(result)
        return result

    def disconnect(self) -> None:
        """Drop the client."""
        self._client = None
        self._pending_task = None
        self.connected = False

    def _card(self) -> Dict[str, Any]:
        last_error = None
        for path in _CARD_PATHS:
            try:
                return self._client.get(path).data or {}
            except HttpStatusError as exc:
                last_error = exc
            except HttpJsonError as exc:
                raise ProtocolError(f"a2a: {exc}") from exc
        raise ProtocolError(f"a2a: no agent card found: {last_error}")

    def _rpc(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        request = {"jsonrpc": "2.0", "id": next(self._ids), "method": method, "params": params}
        try:
            answer = self._client.post(self._rpc_path, request).data or {}
        except HttpJsonError as exc:
            raise ProtocolError(f"a2a: {exc}") from exc
        if "error" in answer:
            raise ProtocolError(f"a2a: {method} failed: {answer['error']}")
        return answer.get("result") or {}

    def _track(self, result: Dict[str, Any]) -> None:
        state = (result.get("status") or {}).get("state")
        if result.get("kind") == "task" or "status" in result:
            self._pending_task = None if state in _TERMINAL else result.get("id")

    def _require(self) -> None:
        if not self.connected or self._client is None:
            raise ProtocolError("A2AAdapter is not connected")
