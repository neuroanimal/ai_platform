"""Unit tests of OpenAICompatibleAdapter, LocalAIAdapter and OllamaAdapter.

Run against an in-process fake server - no model server needed.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

from fake_json_server import FakeJsonServer, openai_chat_answer  # noqa: E402

from ai_platform.common.llm.llm_exception import (  # noqa: E402
    LLMConfigurationError,
    LLMConnectionError,
    LLMNotInitializedError,
    LLMRequestError,
    LLMResponseError,
)
from ai_platform.common.llm.localai_adapter import LocalAIAdapter  # noqa: E402
from ai_platform.common.llm.ollama_adapter import OllamaAdapter  # noqa: E402
from ai_platform.common.llm.openai_compatible_adapter import (  # noqa: E402
    OpenAICompatibleAdapter,
)

CHAT = ("POST", "/v1/chat/completions")
MODELS = ("GET", "/v1/models")


def make(adapter_cls, url, **config):
    """Initialize an adapter against ``url``."""
    adapter = adapter_cls()
    adapter.initialize({"base_url": url, "model": "m", **config})
    return adapter


def test_generate_returns_text_and_sends_openai_payload():
    with FakeJsonServer({CHAT: openai_chat_answer("391")}) as server:
        llm = make(OpenAICompatibleAdapter, server.url, temperature=0, max_tokens=16)
        assert llm.generate("17*23?") == "391"

    body = server.requests[0]["body"]
    assert body["model"] == "m"
    assert body["messages"] == [{"role": "user", "content": "17*23?"}]
    assert body["temperature"] == 0
    assert body["max_tokens"] == 16
    assert body["stream"] is False


def test_chat_completion_metadata_and_truncation():
    with FakeJsonServer({CHAT: openai_chat_answer("abc", finish_reason="length")}) as server:
        result = make(OpenAICompatibleAdapter, server.url).chat_completion(
            [{"role": "user", "content": "x"}]
        )
    assert result.text == "abc"
    assert result.finish_reason == "length"
    assert result.truncated is True
    assert result.usage["total_tokens"] == 8
    assert result.elapsed_seconds > 0
    assert "raw" not in result.to_dict()


def test_call_kwargs_override_defaults_and_pass_through():
    with FakeJsonServer({CHAT: openai_chat_answer("ok")}) as server:
        llm = make(OpenAICompatibleAdapter, server.url, temperature=0.7)
        llm.chat([{"role": "user", "content": "x"}], temperature=0, seed=42, model="other")
    body = server.requests[0]["body"]
    assert body["temperature"] == 0
    assert body["seed"] == 42
    assert body["model"] == "other"


def test_empty_answer_raises_unless_allowed():
    with FakeJsonServer({CHAT: openai_chat_answer("  ")}) as server:
        llm = make(OpenAICompatibleAdapter, server.url)
        with pytest.raises(LLMResponseError):
            llm.generate("x")
        assert llm.chat_completion([{"role": "user", "content": "x"}], allow_empty=True).text == "  "


def test_unexpected_shape_raises_response_error():
    with FakeJsonServer({CHAT: {"choices": []}}) as server:
        with pytest.raises(LLMResponseError):
            make(OpenAICompatibleAdapter, server.url).generate("x")


def test_http_error_becomes_request_error_with_status():
    with FakeJsonServer({CHAT: (400, {"error": "model not found"})}) as server:
        with pytest.raises(LLMRequestError) as info:
            make(OpenAICompatibleAdapter, server.url).generate("x")
    assert info.value.status == 400
    assert "model not found" in str(info.value)


def test_unreachable_server_becomes_connection_error():
    llm = make(OpenAICompatibleAdapter, "http://127.0.0.1:9", timeout=2)
    with pytest.raises(LLMConnectionError):
        llm.generate("x")


def test_list_models_and_health():
    routes = {MODELS: {"object": "list", "data": [{"id": "m"}, {"id": "n"}]}}
    with FakeJsonServer(routes) as server:
        llm = make(OpenAICompatibleAdapter, server.url)
        assert llm.list_models() == ["m", "n"]
        assert llm.health()["model_available"] is True


def test_health_on_unreachable_server_does_not_raise():
    llm = make(OpenAICompatibleAdapter, "http://127.0.0.1:9", timeout=2)
    assert llm.health()["reachable"] is False


def test_api_key_from_env_sent_as_bearer(monkeypatch):
    monkeypatch.setenv("TEST_LLM_KEY", "secret-value")
    with FakeJsonServer({CHAT: openai_chat_answer("ok")}) as server:
        llm = make(OpenAICompatibleAdapter, server.url, api_key_env="TEST_LLM_KEY")
        llm.generate("x")
    assert server.requests[0]["headers"]["authorization"] == "Bearer secret-value"
    # the key must not leak through repr of the client
    assert "secret-value" not in repr(llm._client)  # pylint: disable=protected-access


def test_missing_key_rejected_when_required(monkeypatch):
    class Hosted(OpenAICompatibleAdapter):
        """Provider that needs a key."""
        REQUIRES_API_KEY = True
        DEFAULT_API_KEY_ENV = "TEST_MISSING_KEY"

    monkeypatch.delenv("TEST_MISSING_KEY", raising=False)
    with pytest.raises(LLMConfigurationError, match="TEST_MISSING_KEY"):
        Hosted().initialize({"base_url": "http://x", "model": "m"})


def test_missing_base_url_or_model():
    with pytest.raises(LLMConfigurationError):
        OpenAICompatibleAdapter().initialize({"model": "m"})
    with pytest.raises(LLMConfigurationError):
        OpenAICompatibleAdapter().initialize({"base_url": "http://x"})


def test_invalid_messages():
    llm = make(OpenAICompatibleAdapter, "http://127.0.0.1:9")
    with pytest.raises(LLMConfigurationError):
        llm.chat([])
    with pytest.raises(LLMConfigurationError):
        llm.chat([{"content": "no role"}])


def test_not_initialized_and_after_shutdown():
    llm = OpenAICompatibleAdapter()
    with pytest.raises(LLMNotInitializedError):
        llm.generate("x")
    llm.initialize({"base_url": "http://x", "model": "m"})
    llm.shutdown()
    with pytest.raises(LLMNotInitializedError):
        llm.generate("x")


def test_localai_defaults():
    llm = LocalAIAdapter()
    llm.initialize({"model": "qwen"})
    assert llm.base_url == "http://127.0.0.1:8080"


def test_ollama_openai_path():
    with FakeJsonServer({CHAT: openai_chat_answer("hej")}) as server:
        assert make(OllamaAdapter, server.url).generate("x") == "hej"


def test_ollama_native_chat_maps_options_and_metrics():
    native = {
        "model": "m",
        "message": {"role": "assistant", "content": "odp"},
        "done_reason": "length",
        "total_duration": 3_000_000_000,
        "load_duration": 1_000_000_000,
        "prompt_eval_duration": 500_000_000,
        "eval_duration": 1_000_000_000,
        "prompt_eval_count": 10,
        "eval_count": 20,
    }
    routes = {
        ("POST", "/api/chat"): native,
        ("GET", "/api/version"): {"version": "0.0.test"},
        ("GET", "/api/tags"): {"models": [{"name": "m", "size": 1}]},
    }
    with FakeJsonServer(routes) as server:
        llm = make(OllamaAdapter, server.url, temperature=0)
        result = llm.native_chat_completion(
            [{"role": "user", "content": "x"}], max_tokens=96, num_ctx=1024
        )
        assert llm.version() == "0.0.test"
        assert llm.list_local_models()[0]["name"] == "m"

    options = server.requests[0]["body"]["options"]
    assert options == {"temperature": 0, "num_predict": 96, "num_ctx": 1024}
    assert result.truncated is True
    assert result.metrics["load_seconds"] == pytest.approx(1.0)
    assert result.metrics["tokens_per_second"] == pytest.approx(20.0)
    assert result.usage["total_tokens"] == 30
