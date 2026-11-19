"""Tests of the low-code adapters against in-process fake servers.

They prove the requests and answer handling; no n8n, Flowise or Langflow
server was available live.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

from fake_json_server import FakeJsonServer  # noqa: E402

from ai_platform.common.lowcode.agentgpt_adapter import AgentGPTAdapter  # noqa: E402
from ai_platform.common.lowcode.flowise_adapter import FlowiseAdapter  # noqa: E402
from ai_platform.common.lowcode.langflow_adapter import LangFlowAdapter  # noqa: E402
from ai_platform.common.lowcode.lowcode_support import LowCodeError  # noqa: E402
from ai_platform.common.lowcode.n8n_adapter import N8nAdapter  # noqa: E402
from ai_platform.common.lowcode.rivet_adapter import RivetAdapter  # noqa: E402
from ai_platform.common.lowcode.superagi_adapter import SuperAGIAdapter  # noqa: E402


def test_n8n_deploy_activate_and_webhook():
    workflow = {"name": "echo", "connections": {}, "nodes": [
        {"name": "Webhook", "type": "n8n-nodes-base.webhook", "parameters": {"path": "echo"}}]}
    routes = {("POST", "/api/v1/workflows"): {"id": "w1"},
              ("POST", "/api/v1/workflows/w1/activate"): {"active": True},
              ("POST", "/webhook/echo"): lambda _m, _p, body, _h: (200, {"echo": body})}
    with FakeJsonServer(routes) as server:
        n8n = N8nAdapter()
        n8n.connect({"url": server.url, "api_key": "k"})
        assert n8n.deploy_workflow(workflow) == "w1"
        result = n8n.execute_workflow("w1", {"q": "391?"})
    assert server.requests[0]["headers"]["x-n8n-api-key"] == "k"
    assert server.requests[0]["body"]["settings"] == {}
    assert result == {"workflow_id": "w1", "echo": {"q": "391?"}}
    with pytest.raises(LowCodeError, match="webhook"):
        n8n.execute_workflow("other", {})


def test_n8n_requires_key(monkeypatch):
    monkeypatch.delenv("N8N_API_KEY", raising=False)
    with pytest.raises(LowCodeError, match="N8N_API_KEY"):
        N8nAdapter().connect({})


def test_flowise_chatflow_and_prediction():
    routes = {("POST", "/api/v1/chatflows"): {"id": "cf"},
              ("POST", "/api/v1/prediction/cf"):
                  lambda _m, _p, body, _h: (200, {"text": body["question"].upper()})}
    with FakeJsonServer(routes) as server:
        flowise = FlowiseAdapter()
        flowise.connect({"url": server.url, "api_key": "k"})
        assert flowise.deploy_workflow({"name": "qa", "flowData": {"nodes": [], "edges": []}}) == "cf"
        assert flowise.execute_workflow("cf", {"question": "hej"})["text"] == "HEJ"
    assert json.loads(server.requests[0]["body"]["flowData"]) == {"nodes": [], "edges": []}
    assert server.requests[1]["headers"]["authorization"] == "Bearer k"


def test_langflow_flow_and_run():
    answer = {"outputs": [{"outputs": [{"results": {"message": {"text": "391"}}}]}]}
    routes = {("POST", "/api/v1/flows/"): {"id": "f1"},
              ("POST", "/api/v1/run/f1?stream=false"): answer}
    with FakeJsonServer(routes) as server:
        langflow = LangFlowAdapter()
        langflow.connect({"url": server.url, "api_key": "k"})
        assert langflow.deploy_workflow({"name": "calc", "data": {"nodes": []}}) == "f1"
        result = langflow.execute_workflow("f1", {"input_value": "17*23"})
    assert result["text"] == "391"
    assert server.requests[1]["headers"]["x-api-key"] == "k"
    assert server.requests[1]["body"]["input_type"] == "chat"


@pytest.mark.parametrize("cls", [RivetAdapter, AgentGPTAdapter, SuperAGIAdapter])
def test_refusing_lowcode_adapters(cls):
    with pytest.raises(NotImplementedError, match="N8nAdapter"):
        cls().connect({})
