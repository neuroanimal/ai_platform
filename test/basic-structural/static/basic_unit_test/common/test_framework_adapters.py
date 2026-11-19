"""Tests of the framework adapters.

LangChain runs for real (langchain-core) and once end to end against the
local LocalAI server when it is running. The other frameworks are not
installed here; their adapters are driven with stand-in objects exposing
the method each adapter calls - that proves the wiring, not compatibility
with a real release. Akka and Langdock run against a fake server.
"""

import importlib.util
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(__file__))

from fake_json_server import FakeJsonServer, openai_chat_answer  # noqa: E402

from ai_platform.common.framework.akka_adapter import AkkaAdapter  # noqa: E402
from ai_platform.common.framework.autogen_adapter import AutoGenAdapter  # noqa: E402
from ai_platform.common.framework.autogpt_adapter import AutoGPTAdapter  # noqa: E402
from ai_platform.common.framework.crewai_adapter import CrewAIAdapter  # noqa: E402
from ai_platform.common.framework.framework_support import FrameworkError  # noqa: E402
from ai_platform.common.framework.gradientj_adapter import GradientJAdapter  # noqa: E402
from ai_platform.common.framework.griptape_adapter import GriptapeAdapter  # noqa: E402
from ai_platform.common.framework.haystack_adapter import HaystackAdapter  # noqa: E402
from ai_platform.common.framework.langchain_adapter import LangChainAdapter  # noqa: E402
from ai_platform.common.framework.langdock_adapter import LangDockAdapter  # noqa: E402
from ai_platform.common.framework.langgraph_adapter import LangGraphAdapter  # noqa: E402
from ai_platform.common.framework.langroid_adapter import LangroidAdapter  # noqa: E402
from ai_platform.common.framework.outlines_adapter import OutlinesAdapter  # noqa: E402
from ai_platform.common.framework.semantic_kernel_adapter import SemanticKernelAdapter  # noqa: E402
from ai_platform.common.llm.chat_result import ChatResult  # noqa: E402

LANGCHAIN = pytest.mark.skipif(not importlib.util.find_spec("langchain_core"),
                               reason="langchain-core not installed")


class EchoLLM:
    """Platform-LLM double answering with the prompt in upper case."""

    def chat_completion(self, messages, **_):
        """Answer."""
        return ChatResult(text=messages[-1]["content"].upper(), model="echo")


@LANGCHAIN
def test_langchain_prompt_and_platform_llm():
    adapter = LangChainAdapter()
    adapter.initialize({"prompt": "Pytanie: {q}", "llm": EchoLLM()})
    assert adapter.execute({"input": "ile?"})["output"] == "PYTANIE: ILE?"
    assert adapter.execute({"input": {"q": "x"}})["output"] == "PYTANIE: X"


@LANGCHAIN
def test_langchain_any_runnable():
    from langchain_core.runnables import RunnableLambda  # pylint: disable=import-outside-toplevel
    adapter = LangChainAdapter()
    adapter.initialize({"runnable": RunnableLambda(lambda x: x * 2)})
    assert adapter.execute({"input": 21}) == {"framework": "LangChain", "output": 42, "raw": 42}


@LANGCHAIN
def test_langchain_with_local_llm_live():
    from ai_platform.common.llm.localai_adapter import LocalAIAdapter  # pylint: disable=import-outside-toplevel
    llm = LocalAIAdapter()
    llm.initialize({"base_url": "http://127.0.0.1:8081", "model": "qwen25-05b-localai",
                    "max_tokens": 16, "temperature": 0, "timeout": 120})
    if not llm.health()["model_available"]:
        pytest.skip("LocalAI on :8081 with qwen25-05b-localai not running")
    adapter = LangChainAdapter()
    adapter.initialize({"prompt": "Odpowiedz jednym słowem: {q}", "llm": llm})
    assert adapter.execute({"input": "stolica Polski?"})["output"].strip()


def test_langchain_needs_configuration():
    with pytest.raises(FrameworkError):
        LangChainAdapter().initialize({})


def test_langgraph_compiled_graph_object():
    graph = types.SimpleNamespace(invoke=lambda state, config=None: {**state, "output": "ok"})
    adapter = LangGraphAdapter()
    adapter.initialize({"graph": graph})
    result = adapter.execute({"input": "q"})
    assert result["output"] == "ok" and result["raw"] == {"input": "q", "output": "ok"}


def test_crewai_autogen_sk_griptape_langroid_outlines_haystack():
    crew = types.SimpleNamespace(kickoff=lambda inputs: types.SimpleNamespace(raw=f"crew:{inputs}"))

    async def team_run(task):
        return types.SimpleNamespace(messages=[types.SimpleNamespace(content=f"team:{task}")])

    async def kernel_invoke(function, **arguments):
        return f"{function}:{arguments}"

    cases = [
        (CrewAIAdapter, {"crew": crew}, {"input": {"topic": "x"}}, "crew:{'topic': 'x'}"),
        (AutoGenAdapter, {"agent": types.SimpleNamespace(run=team_run)}, {"input": "go"}, "team:go"),
        (SemanticKernelAdapter, {"kernel": types.SimpleNamespace(invoke=kernel_invoke),
                                 "function": "f"}, {"input": {"a": 1}}, "f:{'a': 1}"),
        (GriptapeAdapter, {"structure": types.SimpleNamespace(
            run=lambda *a: types.SimpleNamespace(output=types.SimpleNamespace(value=f"gt:{a[0]}")))},
         {"input": "hi"}, "gt:hi"),
        (LangroidAdapter, {"task": types.SimpleNamespace(
            run=lambda msg, turns: types.SimpleNamespace(content=f"lr:{msg}:{turns}"))},
         {"input": "hi"}, "lr:hi:-1"),
        (OutlinesAdapter, {"generator": lambda prompt, **kw: {"answer": prompt, **kw}},
         {"input": "p", "kwargs": {"max_tokens": 5}}, {"answer": "p", "max_tokens": 5}),
        (HaystackAdapter, {"pipeline": types.SimpleNamespace(run=lambda data: {"echo": data})},
         {"input": {"llm": {"prompt": "x"}}}, {"echo": {"llm": {"prompt": "x"}}}),
    ]
    for cls, config, task, expected in cases:
        adapter = cls()
        adapter.initialize(config)
        assert adapter.execute(task)["output"] == expected, cls.__name__


@pytest.mark.parametrize("cls", [CrewAIAdapter, AutoGenAdapter, GriptapeAdapter, HaystackAdapter])
def test_missing_native_object(cls):
    adapter = cls()
    adapter.initialize({})
    with pytest.raises(FrameworkError, match="needs config"):
        adapter.execute({"input": "x"})


def test_akka_http():
    routes = {("POST", "/greetings/alice"): lambda _m, _p, body, _h: (200, {"hello": body["name"]}),
              ("GET", "/status"): {"ok": True}}
    with FakeJsonServer(routes) as server:
        akka = AkkaAdapter()
        akka.initialize({"url": server.url})
        assert akka.execute({"path": "/greetings/alice", "input": {"name": "Alice"}})["output"] \
            == {"hello": "Alice"}
        assert akka.execute({"path": "/status"})["output"] == {"ok": True}


def test_langdock_openai_compatible():
    with FakeJsonServer({("POST", "/v1/chat/completions"): openai_chat_answer("odp")}) as server:
        langdock = LangDockAdapter()
        langdock.initialize({"base_url": server.url, "model": "gpt-x", "api_key": "k"})
        assert langdock.execute({"input": "hej"})["output"] == "odp"
    assert server.requests[0]["headers"]["authorization"] == "Bearer k"


def test_langdock_requires_key(monkeypatch):
    monkeypatch.delenv("LANGDOCK_API_KEY", raising=False)
    with pytest.raises(FrameworkError, match="LANGDOCK_API_KEY"):
        LangDockAdapter().initialize({"model": "m"})


@pytest.mark.parametrize("cls", [AutoGPTAdapter, GradientJAdapter])
def test_refusing_framework_adapters(cls):
    with pytest.raises(NotImplementedError, match="instead"):
        cls().execute({"input": "x"})
