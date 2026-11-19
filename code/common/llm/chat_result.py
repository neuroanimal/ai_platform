"""Structured result of one chat completion."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolCall:
    """A function call requested by the model.

    ``arguments`` is the decoded JSON object; ``arguments_error`` is set (and
    ``arguments`` empty) when the model produced arguments that are not a JSON
    object - the agent loop reports that back to the model instead of crashing.
    """

    call_id: str
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    raw_arguments: str = ""
    arguments_error: Optional[str] = None

    def to_message(self) -> Dict[str, Any]:
        """OpenAI ``tool_calls`` entry for an assistant message."""
        return {"id": self.call_id, "type": "function",
                "function": {"name": self.name, "arguments": self.raw_arguments}}


@dataclass
class ChatResult:  # pylint: disable=too-many-instance-attributes
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
    #: Function calls requested by the model (OpenAI tools protocol).
    tool_calls: List[ToolCall] = field(default_factory=list)

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
            "tool_calls": [{"id": c.call_id, "name": c.name, "arguments": c.arguments,
                            "arguments_error": c.arguments_error} for c in self.tool_calls],
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
