"""Unit tests of the hosted-provider LLM adapters.

No real provider is called: HTTP adapters run against an in-process fake
server, Bedrock against a fake boto3 client. What these tests prove is the
request each adapter builds and how it reads the provider's answer shape;
they cannot prove that the provider still accepts that request today.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

from fake_json_server import FakeJsonServer, openai_chat_answer  # noqa: E402

from ai_platform.common.llm.anthropic_adapter import AnthropicAdapter  # noqa: E402
from ai_platform.common.llm.azure_openai_adapter import AzureOpenAIAdapter  # noqa: E402
from ai_platform.common.llm.bedrock_adapter import BedrockAdapter  # noqa: E402
from ai_platform.common.llm.cohere_adapter import CohereAdapter  # noqa: E402
from ai_platform.common.llm.deepseek_adapter import DeepSeekAdapter  # noqa: E402
from ai_platform.common.llm.google_adapter import GoogleAdapter  # noqa: E402
from ai_platform.common.llm.grok_adapter import GrokAdapter  # noqa: E402
from ai_platform.common.llm.huggingface_adapter import HuggingFaceAdapter  # noqa: E402
from ai_platform.common.llm.llm_exception import (  # noqa: E402
    LLMConfigurationError,
    LLMRequestError,
)
from ai_platform.common.llm.mistral_adapter import MistralAdapter  # noqa: E402
from ai_platform.common.llm.openai_adapter import OpenAIAdapter  # noqa: E402
from ai_platform.common.llm.phi_adapter import PhiAdapter  # noqa: E402
from ai_platform.common.llm.qwen_adapter import QwenAdapter  # noqa: E402
from ai_platform.common.llm.replicate_adapter import ReplicateAdapter  # noqa: E402
from ai_platform.common.llm.together_adapter import TogetherAdapter  # noqa: E402

OPENAI_COMPATIBLE_HOSTED = [
    (OpenAIAdapter, "https://api.openai.com", "OPENAI_API_KEY"),
    (DeepSeekAdapter, "https://api.deepseek.com", "DEEPSEEK_API_KEY"),
    (GrokAdapter, "https://api.x.ai", "XAI_API_KEY"),
    (MistralAdapter, "https://api.mistral.ai", "MISTRAL_API_KEY"),
    (TogetherAdapter, "https://api.together.xyz", "TOGETHER_API_KEY"),
    (QwenAdapter, "https://dashscope-intl.aliyuncs.com/compatible-mode", "DASHSCOPE_API_KEY"),
    (HuggingFaceAdapter, "https://router.huggingface.co", "HF_TOKEN"),
    (GoogleAdapter, "https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY"),
]


@pytest.mark.parametrize("cls,url,env", OPENAI_COMPATIBLE_HOSTED)
def test_hosted_defaults_and_key_required(cls, url, env, monkeypatch):
    monkeypatch.delenv(env, raising=False)
    with pytest.raises(LLMConfigurationError, match=env):
        cls().initialize({"model": "m"})

    monkeypatch.setenv(env, "k")
    llm = cls()
    llm.initialize({"model": "m"})
    assert llm.base_url == url


@pytest.mark.parametrize("cls,_url,env", OPENAI_COMPATIBLE_HOSTED)
def test_hosted_chat_roundtrip(cls, _url, env, monkeypatch):
    monkeypatch.setenv(env, "k")
    path = cls.DEFAULT_API_PREFIX + "/chat/completions"
    with FakeJsonServer({("POST", path): openai_chat_answer("ok")}) as server:
        llm = cls()
        llm.initialize({"base_url": server.url, "model": "m"})
        assert llm.generate("x") == "ok"
    assert server.requests[0]["headers"]["authorization"] == "Bearer k"


def test_hosted_no_fabricated_answers_without_server(monkeypatch):
    """The old stubs answered without any server; the real ones must not."""
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    llm = OpenAIAdapter()
    llm.initialize({"base_url": "http://127.0.0.1:9", "model": "m", "timeout": 2})
    with pytest.raises(Exception):
        llm.generate("Hello world")


def test_require_api_key_override_for_local_server():
    llm = HuggingFaceAdapter()
    llm.initialize({"base_url": "http://127.0.0.1:8080", "model": "m", "require_api_key": False})
    assert llm.initialized


def test_azure_paths_and_api_key_header():
    path = "/openai/deployments/dep/chat/completions?api-version=2024-10-21"
    with FakeJsonServer({("POST", path): openai_chat_answer("az")}) as server:
        llm = AzureOpenAIAdapter()
        llm.initialize({"base_url": server.url, "deployment": "dep", "api_key": "k"})
        assert llm.generate("x") == "az"
    assert server.requests[0]["headers"]["api-key"] == "k"
    assert "authorization" not in server.requests[0]["headers"]


def test_phi_requires_explicit_endpoint():
    with pytest.raises(LLMConfigurationError):
        PhiAdapter().initialize({"model": "phi3:mini"})


def test_anthropic_messages_protocol():
    answer = {
        "model": "claude-x",
        "content": [{"type": "text", "text": "Tak."}],
        "stop_reason": "max_tokens",
        "usage": {"input_tokens": 4, "output_tokens": 2},
    }
    with FakeJsonServer({("POST", "/v1/messages"): answer}) as server:
        llm = AnthropicAdapter()
        llm.initialize({"base_url": server.url, "model": "claude-x", "api_key": "k"})
        result = llm.chat_completion([
            {"role": "system", "content": "Be brief."},
            {"role": "user", "content": "Czy?"},
        ])
    request = server.requests[0]
    assert request["headers"]["x-api-key"] == "k"
    assert request["headers"]["anthropic-version"] == "2023-06-01"
    assert request["body"]["system"] == "Be brief."
    assert request["body"]["messages"] == [{"role": "user", "content": "Czy?"}]
    assert request["body"]["max_tokens"] == AnthropicAdapter.DEFAULT_MAX_TOKENS
    assert result.text == "Tak."
    assert result.truncated is True
    assert result.usage["total_tokens"] == 6


def test_cohere_v2_protocol():
    answer = {
        "message": {"role": "assistant", "content": [{"type": "text", "text": "No."}]},
        "finish_reason": "COMPLETE",
        "usage": {"tokens": {"input_tokens": 3, "output_tokens": 1}},
    }
    with FakeJsonServer({("POST", "/v2/chat"): answer}) as server:
        llm = CohereAdapter()
        llm.initialize({"base_url": server.url, "model": "command-x", "api_key": "k"})
        result = llm.chat_completion([{"role": "user", "content": "x"}], max_tokens=5)
    assert server.requests[0]["body"]["max_tokens"] == 5
    assert result.text == "No."
    assert result.finish_reason == "stop"
    assert result.usage["total_tokens"] == 4


def test_replicate_wait_and_poll(monkeypatch):
    monkeypatch.setattr(ReplicateAdapter, "POLL_INTERVAL", 0.01)
    state = {"polls": 0}

    def create(_m, _p, body, headers):
        assert headers["prefer"] == "wait"
        assert body["input"]["prompt"] == "x"
        assert body["input"]["system_prompt"] == "sys"
        return 201, {"id": "p1", "status": "processing",
                     "urls": {"get": server.url + "/v1/predictions/p1"}}

    def poll(_m, _p, _b, _h):
        state["polls"] += 1
        return 200, {"id": "p1", "status": "succeeded", "output": ["39", "1"],
                     "metrics": {"output_token_count": 2}}

    routes = {("POST", "/v1/models/owner/name/predictions"): create,
              ("GET", "/v1/predictions/p1"): poll}
    with FakeJsonServer(routes) as server:
        llm = ReplicateAdapter()
        llm.initialize({"base_url": server.url, "model": "owner/name", "api_key": "k"})
        result = llm.chat_completion([{"role": "system", "content": "sys"},
                                      {"role": "user", "content": "x"}])
    assert result.text == "391"
    assert state["polls"] == 1
    assert result.usage["completion_tokens"] == 2


def test_replicate_failed_prediction():
    routes = {("POST", "/v1/models/o/n/predictions"):
              (201, {"id": "p", "status": "failed", "error": "boom"})}
    with FakeJsonServer(routes) as server:
        llm = ReplicateAdapter()
        llm.initialize({"base_url": server.url, "model": "o/n", "api_key": "k"})
        with pytest.raises(LLMRequestError, match="boom"):
            llm.generate("x")


class FakeBedrockClient:
    """Records the Converse request and returns a scripted answer."""

    def __init__(self, answer):
        self.answer = answer
        self.calls = []

    def converse(self, **request):
        """Mimic bedrock-runtime converse()."""
        self.calls.append(request)
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def test_bedrock_converse_request_and_answer():
    client = FakeBedrockClient({
        "output": {"message": {"role": "assistant", "content": [{"text": "ok"}]}},
        "stopReason": "end_turn",
        "usage": {"inputTokens": 3, "outputTokens": 1, "totalTokens": 4},
        "metrics": {"latencyMs": 250},
    })
    llm = BedrockAdapter()
    llm.initialize({"model": "anthropic.x", "client": client, "max_tokens": 10, "temperature": 0})
    result = llm.chat_completion([{"role": "system", "content": "s"},
                                  {"role": "user", "content": "u"}])
    request = client.calls[0]
    assert request["modelId"] == "anthropic.x"
    assert request["system"] == [{"text": "s"}]
    assert request["messages"] == [{"role": "user", "content": [{"text": "u"}]}]
    assert request["inferenceConfig"] == {"maxTokens": 10, "temperature": 0}
    assert result.text == "ok"
    assert result.finish_reason == "stop"
    assert result.metrics["server_latency_seconds"] == pytest.approx(0.25)


def test_bedrock_error_translated():
    llm = BedrockAdapter()
    llm.initialize({"model": "m", "client": FakeBedrockClient(RuntimeError("AccessDenied"))})
    with pytest.raises(LLMRequestError, match="AccessDenied"):
        llm.generate("x")
