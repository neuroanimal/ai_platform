"""Structured result of one chat completion."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ChatResult:
    """Answer of one chat completion with the metadata benchmarks need.

    ``finish_reason`` follows the OpenAI convention: ``"stop"`` for a
    natural end, ``"length"`` when the token limit cut the answer off.
    ``metrics`` carries server-side timings where the backend reports them
    (e.g. Ollama's ``load_duration``), in seconds.
    """

    text: str
    model: str
    finish_reason: Optional[str] = None
    usage: Dict[str, Any] = field(default_factory=dict)
    elapsed_seconds: float = 0.0
    metrics: Dict[str, float] = field(default_factory=dict)
    raw: Any = field(default=None, repr=False)

    @property
    def truncated(self) -> bool:
        """True when the answer was cut off by the token limit."""
        return self.finish_reason == "length"

    def to_dict(self) -> Dict[str, Any]:
        """Serializable form without the raw server answer."""
        return {
            "text": self.text,
            "model": self.model,
            "finish_reason": self.finish_reason,
            "usage": self.usage,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "metrics": self.metrics,
        }


@dataclass
class StreamChunk:
    """One increment of a streamed answer.

    ``text`` is the new text (may be empty); the last chunk carries
    ``finish_reason`` and, where the server reports it, ``usage``.
    """

    text: str
    finish_reason: Optional[str] = None
    usage: Dict[str, Any] = field(default_factory=dict)
