"""
Fit a conversation into a model's context window, summarizing what does not fit.

A local model has a small window - Ollama gives every model 4096 tokens unless
configured otherwise - and a server that receives more silently drops the
beginning of the prompt. ``fit_messages`` decides explicitly what is sent:

1. system messages (instructions, RAG passages) are always kept;
2. a reserve is left for the answer (``reserve_tokens``);
3. the most recent turns are kept, newest first, as long as they fit; the
   question (the last message) is always kept;
4. older turns that do not fit are replaced by ONE system message holding
   their summary, made by ``summarize`` (any callable, typically the same
   model); without a summarizer they are just dropped.

``ConversationSummarizer`` summarizes incrementally: the summary of the first
N dropped messages is cached, so when turn N+1 also falls out, only that turn
is summarized together with the previous summary - not the whole history again.

Token counts are estimates (``estimate_tokens``: characters / ``CHARS_PER_TOKEN``,
deliberately pessimistic for Polish, plus a per-message overhead), because
Ollama 0.40 has no tokenize endpoint. Pass ``estimate`` to use a real tokenizer.
"""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

#: Characters per token: ~4 for English, ~2.5-3 for Polish with these tokenizers;
#: 2.8 overestimates English a little, which only makes the window safer.
CHARS_PER_TOKEN = 2.8
#: Chat-template tokens around each message (role markers, separators).
MESSAGE_OVERHEAD = 6
SUMMARY_PREFIX = "Summary of the earlier part of this conversation (older messages were " \
                 "removed to fit the context window):\n"

Messages = List[Dict[str, Any]]


class ContextError(Exception):
    """The question alone (with the system messages) does not fit the window."""


def estimate_tokens(text: str) -> int:
    """Pessimistic token estimate of ``text``."""
    return int(len(text or "") / CHARS_PER_TOKEN) + 1


def message_tokens(message: Dict[str, Any],
                   estimate: Callable[[str], int] = estimate_tokens) -> int:
    """Estimated tokens of one message including the template overhead."""
    return estimate(str(message.get("content") or "")) + MESSAGE_OVERHEAD


@dataclass
class ContextReport:  # pylint: disable=too-many-instance-attributes
    """What ``fit_messages`` did."""

    context_tokens: int
    reserve_tokens: int
    prompt_tokens: int = 0
    kept_messages: int = 0
    dropped_messages: int = 0
    summarized: bool = False
    summary_tokens: int = 0
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serializable form."""
        return dict(self.__dict__)


def default_reserve(context_tokens: int, max_tokens: Optional[int] = None) -> int:
    """Tokens kept free for the answer: a quarter of the window, 512 at least."""
    reserve = max(512, context_tokens // 4)
    return min(reserve, max_tokens) if max_tokens else reserve


def fit_messages(messages: Messages, context_tokens: int, *,  # pylint: disable=too-many-locals
                 reserve_tokens: Optional[int] = None,
                 summarize: Optional[Callable[[Messages], str]] = None,
                 estimate: Callable[[str], int] = estimate_tokens
                 ) -> Tuple[Messages, ContextReport]:
    """Messages that fit ``context_tokens`` (minus the reserve), and a report."""
    reserve = default_reserve(context_tokens) if reserve_tokens is None else reserve_tokens
    report = ContextReport(context_tokens, reserve)
    system = [m for m in messages if m.get("role") == "system"]
    turns = [m for m in messages if m.get("role") != "system"]
    budget = context_tokens - reserve - sum(message_tokens(m, estimate) for m in system)
    if not turns:
        report.prompt_tokens = context_tokens - reserve - budget
        return list(messages), report
    kept: Messages = []
    used = 0
    for message in reversed(turns):
        cost = message_tokens(message, estimate)
        if kept and used + cost > budget:
            break
        kept.insert(0, message)
        used += cost
    if used > budget:
        raise ContextError(f"the question needs ~{used} tokens but only ~{max(budget, 0)} are "
                           f"free in a {context_tokens}-token window (reserve {reserve})")
    dropped = turns[:len(turns) - len(kept)]
    summary_message: Messages = []
    if dropped and summarize is not None:
        summary = SUMMARY_PREFIX + summarize(dropped).strip()
        summary_message = [{"role": "system", "content": summary}]
        cost = message_tokens(summary_message[0], estimate)
        while len(kept) > 1 and used + cost > budget:  # make room for the summary
            used -= message_tokens(kept[0], estimate)
            dropped.append(kept.pop(0))
            report.notes.append("a kept turn gave way to the summary")
        if used + cost > budget:
            summary_message = []
            report.notes.append("summary did not fit and was left out")
        else:
            report.summarized, report.summary_tokens = True, cost
            used += cost
    report.kept_messages, report.dropped_messages = len(kept), len(dropped)
    report.prompt_tokens = (context_tokens - reserve - budget) + used
    return system + summary_message + kept, report


def _key(messages: Sequence[Dict[str, Any]]) -> str:
    data = json.dumps([[m.get("role"), m.get("content")] for m in messages], ensure_ascii=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


SUMMARY_INSTRUCTION = (
    "Summarize the conversation below in at most 150 words. Keep facts, numbers, names, "
    "decisions and open questions; leave out greetings. Write in the language of the "
    "conversation. Reply with the summary only.")


class ConversationSummarizer:  # pylint: disable=too-few-public-methods
    """Incremental, cached summaries of dropped messages.

    ``complete(prompt) -> str`` produces text (e.g. a guarded call of the chat
    model). The cache maps a prefix of dropped messages to its summary.
    """

    def __init__(self, complete: Callable[[str], str], max_entries: int = 256) -> None:
        self.complete = complete
        self.max_entries = max_entries
        self._cache: Dict[str, str] = {}

    def __call__(self, dropped: Messages) -> str:
        for size in range(len(dropped), 0, -1):
            cached = self._cache.get(_key(dropped[:size]))
            if cached is not None:
                if size == len(dropped):
                    return cached
                return self._remember(dropped, self._summarize(cached, dropped[size:]))
        return self._remember(dropped, self._summarize("", dropped))

    def _summarize(self, previous: str, messages: Messages) -> str:
        lines = [f"{m.get('role')}: {m.get('content')}" for m in messages]
        prompt = SUMMARY_INSTRUCTION + "\n\n"
        if previous:
            prompt += f"SUMMARY SO FAR:\n{previous}\n\nNEWER MESSAGES:\n"
        return self.complete(prompt + "\n".join(lines)).strip()

    def _remember(self, dropped: Messages, summary: str) -> str:
        if len(self._cache) >= self.max_entries:
            self._cache.pop(next(iter(self._cache)))
        self._cache[_key(dropped)] = summary
        return summary
