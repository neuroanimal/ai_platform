"""n8n adapter (n8n public REST API + webhook trigger).

- ``deploy_workflow(workflow)``: ``POST /api/v1/workflows`` with the
  workflow JSON exported from the n8n editor (name, nodes, connections,
  settings), then ``POST /api/v1/workflows/<id>/activate`` unless
  ``activate`` is False. Returns the workflow id.
- ``execute_workflow(id, inputs)``: n8n's public API has no "run now"
  operation; workflows run from triggers. The adapter calls the workflow's
  *Webhook* trigger: ``POST /webhook/<path>`` with ``inputs`` as JSON body.
  The path is taken from the workflow's Webhook node when it was deployed
  through this adapter, else from ``inputs["_webhook_path"]``.

Configuration: ``url`` (default http://127.0.0.1:5678), ``api_key`` /
``api_key_env`` (default env N8N_API_KEY, sent as X-N8N-API-KEY),
``activate`` (default True).

Not verified against a running n8n here; unit tests use a fake server.
Previously a stub returning fabricated ids; the class name and the
LowCodeAdapter methods are unchanged.
"""

from typing import Any, Dict

from ai_platform.common.lowcode.lowcode_support import LowCodeBase, LowCodeError

WEBHOOK_NODE = "n8n-nodes-base.webhook"


class N8nAdapter(LowCodeBase):
    """Workflows on n8n."""

    PLATFORM = "n8n"
    DEFAULT_URL = "http://127.0.0.1:5678"
    KEY_HEADER = "X-N8N-API-KEY"
    KEY_SCHEME = ""
    KEY_ENV = "N8N_API_KEY"
    KEY_REQUIRED = True

    def __init__(self):
        super().__init__()
        self.activate = True
        self.webhook_paths: Dict[str, str] = {}

    def _configure(self, config: Dict[str, Any]) -> None:
        self.activate = bool(config.get("activate", True))

    def deploy_workflow(self, workflow: Dict[str, Any]) -> str:
        """Create (and activate) the workflow; return its id."""
        body = {key: workflow[key] for key in ("name", "nodes", "connections", "settings")
                if key in workflow}
        body.setdefault("settings", {})
        if "name" not in body or "nodes" not in body:
            raise LowCodeError("n8n: workflow needs 'name' and 'nodes'")
        created = self._call("POST", "/api/v1/workflows", body)
        workflow_id = str(created["id"])
        for node in workflow.get("nodes", []):
            if node.get("type") == WEBHOOK_NODE and node.get("parameters", {}).get("path"):
                self.webhook_paths[workflow_id] = node["parameters"]["path"]
        if self.activate:
            self._call("POST", f"/api/v1/workflows/{workflow_id}/activate", {})
        return workflow_id

    def execute_workflow(self, workflow_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger the workflow's webhook with ``inputs``."""
        inputs = dict(inputs or {})
        path = inputs.pop("_webhook_path", None) or self.webhook_paths.get(str(workflow_id))
        if not path:
            raise LowCodeError(f"n8n: no webhook path known for workflow {workflow_id}; "
                               "pass inputs['_webhook_path']")
        answer = self._call("POST", f"/webhook/{path.lstrip('/')}", inputs)
        result = answer if isinstance(answer, dict) else {"data": answer}
        return {"workflow_id": str(workflow_id), **result}
