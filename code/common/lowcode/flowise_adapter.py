"""Flowise adapter (Flowise REST API).

- ``deploy_workflow(workflow)``: ``POST /api/v1/chatflows`` with
  ``{"name": ..., "flowData": <the flow JSON exported from Flowise>}``;
  returns the chatflow id.
- ``execute_workflow(id, inputs)``: ``POST /api/v1/prediction/<id>`` with
  ``{"question": inputs["question"], "overrideConfig": ..., "history": ...}``;
  returns Flowise's answer (``text`` holds the reply).

Configuration: ``url`` (default http://127.0.0.1:3000), ``api_key`` /
``api_key_env`` (default env FLOWISE_API_KEY, Bearer).

Not verified against a running Flowise here; unit tests use a fake server.
Previously a stub returning fabricated ids; the class name and the
LowCodeAdapter methods are unchanged.
"""

import json
from typing import Any, Dict

from ai_platform.common.lowcode.lowcode_support import LowCodeBase, LowCodeError


class FlowiseAdapter(LowCodeBase):
    """Chatflows on Flowise."""

    PLATFORM = "flowise"
    DEFAULT_URL = "http://127.0.0.1:3000"
    KEY_ENV = "FLOWISE_API_KEY"

    def deploy_workflow(self, workflow: Dict[str, Any]) -> str:
        """Create a chatflow; return its id."""
        if "name" not in workflow or "flowData" not in workflow:
            raise LowCodeError("flowise: workflow needs 'name' and 'flowData'")
        flow = workflow["flowData"]
        created = self._call("POST", "/api/v1/chatflows", {
            "name": workflow["name"],
            "flowData": flow if isinstance(flow, str) else json.dumps(flow),
            "deployed": bool(workflow.get("deployed", True))})
        return str(created["id"])

    def execute_workflow(self, workflow_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Run a prediction; return Flowise's answer."""
        if "question" not in (inputs or {}):
            raise LowCodeError("flowise: inputs need 'question'")
        body = {k: inputs[k] for k in ("question", "overrideConfig", "history", "uploads")
                if k in inputs}
        answer = self._call("POST", f"/api/v1/prediction/{workflow_id}", body)
        result = answer if isinstance(answer, dict) else {"text": str(answer)}
        return {"workflow_id": str(workflow_id), **result}
