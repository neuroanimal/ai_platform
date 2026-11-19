"""Tests of the prompt adapters (Jinja2, LangChain and Priompt run for real)."""

import importlib.util
import types

import pytest

from ai_platform.common.prompt.guidance_adapter import GuidanceAdapter
from ai_platform.common.prompt.jinja2_prompt_adapter import Jinja2PromptAdapter, PromptError
from ai_platform.common.prompt.langchain_prompt_adapter import LangChainPromptAdapter
from ai_platform.common.prompt.lmql_adapter import LMQLAdapter
from ai_platform.common.prompt.priompt_adapter import PriomptAdapter
from ai_platform.common.prompt.promptlayer_adapter import PromptLayerAdapter


def test_jinja2_renders_named_and_inline_templates():
    adapter = Jinja2PromptAdapter()
    # trim_blocks: the newline right after a block tag is removed, so it goes before it.
    adapter.initialize({"templates": {
        "q": "Pytanie: {{ q }}\n{% if ctx %}Kontekst: {{ ctx }}{% endif %}"}})
    assert adapter.render("q", {"q": "Ile?", "ctx": "391"}) == "Pytanie: Ile?\nKontekst: 391"
    assert adapter.render("Hej {{ name }}", {"name": "Bielik"}) == "Hej Bielik"


def test_jinja2_strict_undefined_and_sandbox():
    adapter = Jinja2PromptAdapter()
    adapter.initialize({})
    with pytest.raises(PromptError):
        adapter.render("{{ missing }}", {})
    with pytest.raises(PromptError):
        adapter.render("{{ x.__class__.__mro__[1].__subclasses__() }}", {"x": ""})


@pytest.mark.skipif(not importlib.util.find_spec("langchain_core"),
                    reason="langchain-core not installed")
@pytest.mark.parametrize("fmt,template", [("f-string", "Hello {name}"),
                                          ("mustache", "Hello {{name}}")])
def test_langchain_prompt_formats(fmt, template):
    adapter = LangChainPromptAdapter()
    adapter.initialize({"template_format": fmt})
    assert adapter.render(template, {"name": "World"}) == "Hello World"
    with pytest.raises(PromptError, match="name"):
        adapter.render(template, {})


def test_priompt_keeps_everything_within_budget():
    adapter = PriomptAdapter()
    adapter.initialize({"token_budget": 1000})
    text = adapter.render("{system}\n{history}\nQ: {q}", {
        "system": "Be brief.",
        "history": [{"text": "old turn", "priority": 1}, {"text": "new turn", "priority": 5}],
        "q": "Ile?"})
    assert text == "Be brief.\nold turn\nnew turn\nQ: Ile?"
    assert adapter.last_dropped == []


def test_priompt_drops_lowest_priority_first():
    words = len  # 1 "token" per character keeps the arithmetic obvious
    adapter = PriomptAdapter()
    adapter.initialize({"token_budget": 30, "count_tokens": words})
    text = adapter.render("{history}|{q}", {
        "history": [{"text": "AAAAAAAAAA", "priority": 1},
                    {"text": "BBBBBBBBBB", "priority": 3},
                    {"text": "CCCCCCCCCC", "priority": 2}],
        "q": "Q?"})
    assert text == "BBBBBBBBBB\nCCCCCCCCCC|Q?"
    assert [d["text"] for d in adapter.last_dropped] == ["AAAAAAAAAA"]


def test_priompt_raises_when_required_parts_exceed_budget():
    adapter = PriomptAdapter()
    adapter.initialize({"token_budget": 5, "count_tokens": len})
    with pytest.raises(PromptError, match="budget"):
        adapter.render("{q}", {"q": "far too long for five", "x": {"text": "drop", "priority": 1}})


def test_promptlayer_with_fake_client():
    calls = []

    def get(name, params):
        calls.append((name, params))
        return {"prompt_template": {"type": "chat", "messages": [
            {"role": "system", "content": [{"type": "text", "text": "Be brief."}]},
            {"role": "user", "content": [{"type": "text", "text": f"Q: {params['input_variables']['q']}"}]}]}}

    client = types.SimpleNamespace(templates=types.SimpleNamespace(get=get))
    adapter = PromptLayerAdapter()
    adapter.initialize({"client": client, "label": "prod"})
    assert adapter.render("qa", {"q": "Ile?"}) == "system: Be brief.\nuser: Q: Ile?"
    assert calls[0] == ("qa", {"input_variables": {"q": "Ile?"}, "label": "prod"})


def test_promptlayer_requires_key(monkeypatch):
    monkeypatch.delenv("PROMPTLAYER_API_KEY", raising=False)
    with pytest.raises(PromptError):
        PromptLayerAdapter().initialize({})


@pytest.mark.parametrize("cls", [GuidanceAdapter, LMQLAdapter])
def test_refusing_prompt_adapters(cls):
    with pytest.raises(NotImplementedError, match="Jinja2PromptAdapter"):
        cls().render("x", {})
