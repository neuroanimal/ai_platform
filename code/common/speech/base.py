"""Adapter contract for every speech stack.

A class declares which directions it implements. Calling a direction it does
not implement raises ``SpeechCapabilityError`` instead of returning a placeholder.
"""

from abc import ABC
from typing import Any, Dict, Optional

from ai_platform.common.speech.models import SpeechExchange, SynthesisResult, Transcript
from ai_platform.common.speech.speech_exception import SpeechCapabilityError, SpeechConfigError


class SpeechAdapter(ABC):
    """Lifecycle shared with the LLM adapters: initialize, use, shutdown.

    Concrete classes set ``NAME`` and ``CAPABILITIES`` (``tts``, ``stt``, ``sts``).
    """

    NAME = ""
    CAPABILITIES = frozenset()

    def __init__(self) -> None:
        self.ready = False
        self.config: Dict[str, Any] = {}

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Remember configuration. Subclasses call this, then load their backend."""
        self.config = dict(config or {})
        self.ready = True

    def shutdown(self) -> None:
        """Release nothing by default. Override when a process or socket is held."""
        self.ready = False

    def _require_ready(self) -> None:
        if not self.ready:
            raise SpeechConfigError(f"{type(self).__name__} is not initialized")

    def _unsupported(self, capability: str):
        raise SpeechCapabilityError(
            f"{type(self).__name__} does not implement {capability} "
            f"(has: {', '.join(sorted(self.CAPABILITIES)) or 'none'})"
        )

    def synthesize(self, text: str, **kwargs) -> SynthesisResult:  # pylint: disable=unused-argument
        """Text to speech."""
        self._require_ready()
        return self._unsupported("tts")

    def transcribe(self, audio, **kwargs) -> Transcript:  # pylint: disable=unused-argument
        """Speech to text."""
        self._require_ready()
        return self._unsupported("stt")

    def converse(self, audio, **kwargs) -> SpeechExchange:  # pylint: disable=unused-argument
        """Speech to speech."""
        self._require_ready()
        return self._unsupported("sts")
