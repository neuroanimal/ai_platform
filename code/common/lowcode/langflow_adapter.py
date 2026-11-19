"""Langflow adapter (Langflow REST API).

- ``deploy_workflow(workflow)``: ``POST /api/v1/flows/`` with
  ``{"name", "description", "data": <the flow JSON exported from Langflow>}``;
  returns the flow id.
- ``execute_workflow(id, inputs)``: ``POST /api/v1/run/<id>?stream=false``
  with ``{"input_value": inputs["input_value"], "input_type": "chat",
  "output_type": "chat", "tweaks": ...}``. Returns Langflow's answer with
  the first chat message text extracted into ``text``.

Configuration: ``url`` (default http://127.0.0.1:7860), ``api_key`` /
``api_key_env`` (default env LANGFLOW_API_KEY, sent as ``x-api-key``).

Not verified against a running Langflow here; unit tests use a fake
server. Previously a stub returning fabricated ids; the class name and the
LowCodeAdapter methods are unchanged.
"""

from typing import Any, Dict, Optional

from ai_platform.common.lowcode.lowcode_support import LowCodeBase, LowCodeError


def first_message_text(answer: Dict[str, Any]) -> Optional[str]:
    """outputs[0].outputs[0].results.message.text, tolerating older shapes."""
    try:
        result = answer["outputs"][0]["outputs"][0]
    except (KeyError, IndexError, TypeError):
        return None
    message = (result.get("results") or {}).get("message") or {}
    if isinstance(message, dict) and message.get("text") is not None:
        return message["text"]
    for container in ("messages", "artifacts"):
        value = result.get(container)
        if isinstance(value, list) and value and isinstance(value[0], dict):
            return value[0].get("message") or value[0].get("text")
    return None


class LangFlowAdapter(LowCodeBase):
    """Flows on Langflow."""

    PLATFORM = "langflow"
    DEFAULT_URL = "http://127.0.0.1:7860"
    KEY_HEADER = "x-api-key"
    KEY_SCHEME = ""
    KEY_ENV = "LANGFLOW_API_KEY"

    def deploy_workflow(self, workflow: Dict[str, Any]) -> str:
        """Create a flow; return its id."""
        if "name" not in workflow or "data" not in workflow:
            raise LowCodeError("langflow: workflow needs 'name' and 'data'")
        created = self._call("POST", "/api/v1/flows/", {
            "name": workflow["name"], "description": workflow.get("description", ""),
            "data": workflow["data"]})
        return str(created["id"])

    def execute_workflow(self, workflow_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Run the flow once (non-streaming)."""
        inputs = dict(inputs or {})
        body = {"input_value": str(inputs.get("input_value", "")),
                "input_type": inputs.get("input_type", "chat"),
                "output_type": inputs.get("output_type", "chat"),
                **({"tweaks": inputs["tweaks"]} if "tweaks" in inputs else {})}
        answer = self._call("POST", f"/api/v1/run/{workflow_id}?stream=false", body) or {}
        return {"workflow_id": str(workflow_id), "text": first_message_text(answer), **answer}
