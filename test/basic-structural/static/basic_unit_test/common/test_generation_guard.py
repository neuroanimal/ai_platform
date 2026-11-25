"""Unit tests of generation_guard: loop detection, time budget, timestamps, reasoning."""

import itertools

from ai_platform.common.llm.chat_result import StreamChunk
from ai_platform.common.llm.generation_guard import find_loop, guarded_chat, guarded_stream

# Real output of llama3.2:3b in the agent-RAG benchmark (2026-11-24).
LOOPING = "[1] Dziesięć razy dwanaście" + " razy dwanaście" * 12


def test_find_loop_real_case_and_non_loops():
    assert find_loop(LOOPING) == " razy dwanaście"
    assert find_loop(LOOPING + " razy dwa") == "naście razy dwa"  # any phase of the unit
    table = "| a | b |\n" + "|---|---|\n" + "| 1 | 2 |\n| 3 | 4 |\n"
    assert find_loop(table + "-" * 400) is None          # no letter in the unit
    assert find_loop("Ala ma kota. " * 9) is None        # 9 < 10 repetitions
    assert find_loop("Ala ma kota. " * 10) is not None
    assert find_loop("ha" * 10) is None                  # shorter than the minimum span
    assert find_loop("To jest zwykła odpowiedź bez powtórzeń, 17 * 23 = 391.") is None


def _chunks(texts, closed):
    def gen():
        try:
            for text in texts:
                yield StreamChunk(text)
            yield StreamChunk("", "stop")
        finally:
            closed.append(True)
    return gen()


def test_loop_stops_stream_and_closes_it():
    closed = []
    timing = {}
    words = ["Wynik:"] + [" razy dwanaście"] * 200
    out = list(guarded_stream(_chunks(words, closed), timing=timing))
    assert out[-1].finish_reason == "loop" and closed == [True]
    assert len(out) < 60  # stopped long before the 200 repetitions
    assert timing["loop_in"] == "answer" and "dwanaście" in timing["loop_unit"]
    assert {"request_sent_utc", "first_token_utc", "finished_utc", "elapsed_seconds",
            "first_token_seconds"} <= set(timing)


def test_time_budget_with_fake_clock():
    ticks = itertools.count(0, 1.0)  # one second per clock() call
    closed = []
    out = list(guarded_stream(_chunks([f"słowo{n} " for n in range(100)], closed),
                              max_seconds=5, loop_repeats=None, clock=lambda: next(ticks)))
    assert out[-1].finish_reason == "time_limit" and closed == [True]
    assert len(out) < 10


def test_natural_end_and_reasoning_collected():
    class Reasoner:
        """Streams reasoning first, then the answer."""
        model = "r"

        @staticmethod
        def stream_chat(messages, **_):
            """Two reasoning chunks, one answer chunk, end."""
            assert messages
            yield StreamChunk("", reasoning="17*23 = 17*20 + 17*3 = ")
            yield StreamChunk("", reasoning="340 + 51 = 391")
            yield StreamChunk("391", "stop", {"completion_tokens": 9})

    result = guarded_chat(Reasoner(), [{"role": "user", "content": "17*23?"}], max_seconds=60)
    assert result.text == "391" and result.finish_reason == "stop"
    assert result.reasoning.endswith("391") and result.usage["completion_tokens"] == 9
    assert "stopped_by" not in result.metrics["timing"]
