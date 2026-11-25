"""Unit tests of context_window: fitting a conversation and incremental summaries."""

import pytest

from ai_platform.common.llm.context_window import (
    SUMMARY_PREFIX,
    ContextError,
    ConversationSummarizer,
    estimate_tokens,
    fit_messages,
)


def _conversation(turns, size=300):
    messages = [{"role": "system", "content": "Jesteś pomocnym asystentem."}]
    for number in range(turns):
        messages.append({"role": "user", "content": f"Pytanie {number}: " + "x" * size})
        messages.append({"role": "assistant", "content": f"Odpowiedź {number}: " + "y" * size})
    messages.append({"role": "user", "content": "Ostatnie pytanie?"})
    return messages


def test_short_conversation_is_sent_whole():
    messages = _conversation(2)
    fitted, report = fit_messages(messages, 4096)
    assert fitted == messages and report.dropped_messages == 0 and not report.summarized


def test_long_conversation_keeps_system_and_newest_turns():
    messages = _conversation(40)
    fitted, report = fit_messages(messages, 4096, reserve_tokens=1024)
    assert fitted[0] == messages[0] and fitted[-1] == messages[-1]
    assert report.dropped_messages > 0 and report.prompt_tokens <= 4096 - 1024
    assert fitted[1:] == messages[-len(fitted) + 1:]  # a contiguous tail, newest last


def test_dropped_turns_replaced_by_summary():
    seen = []

    def summarize(dropped):
        seen.append(len(dropped))
        return "Rozmawialiśmy o pytaniach 0-30."

    fitted, report = fit_messages(_conversation(40), 4096, reserve_tokens=1024,
                                  summarize=summarize)
    assert report.summarized and len(seen) == 1 and seen[0] <= report.dropped_messages
    summary = [m for m in fitted if m["content"].startswith(SUMMARY_PREFIX)]
    assert len(summary) == 1 and fitted.index(summary[0]) == 1  # right after the system prompt


def test_question_too_long_raises():
    with pytest.raises(ContextError):
        fit_messages([{"role": "user", "content": "x" * 20000}], 4096)


def test_summarizer_is_incremental_and_cached():
    prompts = []

    def complete(prompt):
        prompts.append(prompt)
        return f"streszczenie {len(prompts)}"

    summarizer = ConversationSummarizer(complete)
    first = [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]
    assert summarizer(first) == "streszczenie 1"
    assert summarizer(first) == "streszczenie 1" and len(prompts) == 1  # cached
    longer = first + [{"role": "user", "content": "c"}]
    assert summarizer(longer) == "streszczenie 2"
    assert "SUMMARY SO FAR:\nstreszczenie 1" in prompts[1] and "user: a" not in prompts[1]


def test_estimate_is_pessimistic_for_polish():
    assert estimate_tokens("Zażółć gęślą jaźń") >= 5
