"""
Guards for local generation: a time budget instead of a token budget, loop detection
and timestamps.

A local model costs no credits, so a token limit is only a crude way of saying
"do not take forever". These guards say it directly:

- ``max_seconds``: the answer is stopped when the wall-clock time since the
  request exceeds the budget (``finish_reason = "time_limit"``). Local models
  of different speed and verbosity therefore get the same TIME, not the same
  number of tokens - a reasoning model may think for 2000 tokens if it is
  fast enough. The token limit can stay high (``max_tokens``), as a backstop.
- loop detection: small models sometimes repeat a phrase forever ("razy
  dwanaście razy dwanaście ..."). When the end of the answer (or of the
  reasoning) is the same unit repeated ``loop_repeats`` times, generation is
  stopped (``finish_reason = "loop"``) and the repeated unit is reported.
- timestamps: every guarded call records when the request was sent, when the
  first token arrived and when the answer ended - as absolute UTC timestamps
  and as seconds relative to the request.

Stopping works by closing the stream: the HTTP connection is closed and the
server (Ollama, llama.cpp, LocalAI) stops generating. ``stream_chat`` of the
OpenAI-compatible adapters is used, so this works for every provider that
streams. Text the model "thinks" (``reasoning``, e.g. qwen3) is collected
separately from the answer.
"""

import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional

from ai_platform.common.llm.chat_result import ChatResult, StreamChunk

#: Default number of consecutive repetitions that count as a loop.
LOOP_REPEATS = 10
#: Shortest and longest repeated unit (characters) that is looked for.
MIN_UNIT, MAX_UNIT = 2, 400
#: A loop must span at least this many characters (so "ha" x 10 is not one).
MIN_LOOP_SPAN = 80
#: How often (new characters) the loop check runs; it scans the tail only.
CHECK_EVERY = 64
_WORD = re.compile(r"\w")


def find_loop(text: str, repeats: int = LOOP_REPEATS, min_unit: int = MIN_UNIT,
              max_unit: int = MAX_UNIT, min_span: int = MIN_LOOP_SPAN) -> Optional[str]:
    """The unit the end of ``text`` repeats at least ``repeats`` times, or None.

    The unit must contain a letter or digit, so rows of "-" or "=" in a
    Markdown table are not loops; it is taken as the last ``n`` characters, so
    a loop is found whatever phase the text ends in.
    """
    tail = text[-(max_unit * repeats + max_unit):]
    for size in range(min_unit, min(max_unit, len(tail) // repeats) + 1):
        unit = tail[-size:]
        needed = max(repeats, -(-min_span // size))
        if size * needed > len(tail) or not _WORD.search(unit):
            continue
        if tail.endswith(unit * needed):
            return unit
    return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def guarded_stream(chunks: Iterator[StreamChunk], *, max_seconds: Optional[float] = None,  # pylint: disable=too-many-locals,too-many-branches
                   loop_repeats: Optional[int] = LOOP_REPEATS,
                   timing: Optional[Dict[str, Any]] = None,
                   clock=time.monotonic) -> Iterator[StreamChunk]:
    """Pass ``chunks`` through; stop on the time budget or a loop.

    When it stops early, the last chunk yielded has ``finish_reason`` "time_limit"
    or "loop". ``timing`` (a dict, filled in place) gets the timestamps and,
    for a loop, ``loop_unit`` and ``loop_in`` ("answer" or "reasoning").
    """
    timing = timing if timing is not None else {}
    start = clock()
    timing.setdefault("request_sent_utc", _now())
    texts = {"answer": [], "reasoning": []}
    sizes = {"answer": 0, "reasoning": 0}
    checked = {"answer": 0, "reasoning": 0}
    stop: Optional[str] = None
    try:
        for chunk in chunks:
            if (chunk.text or chunk.reasoning) and "first_token_utc" not in timing:
                timing["first_token_utc"] = _now()
                timing["first_token_seconds"] = round(clock() - start, 3)
            for part, value in (("answer", chunk.text), ("reasoning", chunk.reasoning)):
                if value:
                    texts[part].append(value)
                    sizes[part] += len(value)
            yield chunk
            if chunk.finish_reason:
                break
            if max_seconds is not None and clock() - start > max_seconds:
                stop = "time_limit"
                break
            for part in ("answer", "reasoning"):
                if loop_repeats and sizes[part] - checked[part] >= CHECK_EVERY:
                    checked[part] = sizes[part]
                    texts[part] = ["".join(texts[part])]
                    unit = find_loop(texts[part][0], loop_repeats)
                    if unit is not None:
                        stop = "loop"
                        timing.update(loop_unit=unit, loop_in=part, loop_repeats=loop_repeats)
                        break
            if stop:
                break
    finally:
        if hasattr(chunks, "close"):
            chunks.close()  # closes the HTTP stream: the server stops generating
        timing["finished_utc"] = _now()
        timing["elapsed_seconds"] = round(clock() - start, 3)
        if stop:
            timing["stopped_by"] = stop
    if stop:
        yield StreamChunk("", stop)


def guarded_chat(llm, messages: List[Dict[str, Any]], *, max_seconds: Optional[float] = None,
                 loop_repeats: Optional[int] = LOOP_REPEATS, **kwargs) -> ChatResult:
    """One streamed completion under the guards, as a ChatResult.

    ``result.metrics["timing"]`` holds the timestamps; ``result.reasoning`` the
    model's reasoning text, if it sent any; ``finish_reason`` is "stop",
    "length", "time_limit" or "loop".
    """
    timing: Dict[str, Any] = {}
    text: List[str] = []
    reasoning: List[str] = []
    finish, usage = None, {}
    for chunk in guarded_stream(llm.stream_chat(messages, **kwargs), max_seconds=max_seconds,
                                loop_repeats=loop_repeats, timing=timing):
        text.append(chunk.text or "")
        reasoning.append(chunk.reasoning or "")
        finish = chunk.finish_reason or finish
        usage = chunk.usage or usage
    return ChatResult(text="".join(text), model=getattr(llm, "model", "") or "",
                      finish_reason=finish, usage=usage,
                      elapsed_seconds=timing.get("elapsed_seconds", 0.0),
                      metrics={"timing": timing}, reasoning="".join(reasoning))
