"""Speech to speech by composition: STT, then a text function, then TTS.

The text function is the seam to the rest of the platform. An LLM adapter
fits if you pass ``llm_reply_transform(llm)`` from the speech service; a
rule, a prompt template or the identity function also fit. This module does
not import ``common.llm``, so the speech domain stays usable without it.
"""

# pylint: disable=attribute-defined-outside-init  # adapters set their backend state in initialize(), as in the LLM adapters

from typing import Any, Callable, Dict, Optional

from ai_platform.common.speech.base import SpeechAdapter
from ai_platform.common.speech.checks import require_audio, require_text
from ai_platform.common.speech.models import SpeechExchange
from ai_platform.common.speech.speech_exception import SpeechConfigError, SpeechResponseError


class CascadeSTSAdapter(SpeechAdapter):
    """Registry name: ``cascade``. Capabilities: sts, and it can also relay tts/stt."""

    NAME = "cascade"
    CAPABILITIES = frozenset({"sts", "stt", "tts"})

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        SpeechAdapter.initialize(self, config)
        stt = self.config.get("stt")
        tts = self.config.get("tts")
        if stt is None or tts is None:
            self.ready = False
            raise SpeechConfigError("CascadeSTSAdapter requires config['stt'] and config['tts']")
        self.stt = stt
        self.tts = tts
        self.transform: Callable[[str], str] = self.config.get("transform") or (lambda heard: heard)

    def transcribe(self, audio, **kwargs):
        self._require_ready()
        return self.stt.transcribe(audio, **kwargs)

    def synthesize(self, text, **kwargs):
        self._require_ready()
        return self.tts.synthesize(text, **kwargs)

    def converse(self, audio, **kwargs) -> SpeechExchange:
        self._require_ready()
        buffer = require_audio(audio)
        transcript = self.stt.transcribe(buffer, **kwargs.get("stt_kwargs", {}))
        if not transcript.text.strip():
            raise SpeechResponseError("cascade STT returned an empty transcript")
        try:
            reply = self.transform(transcript.text)
        except SpeechResponseError:
            raise
        except Exception as exc:
            raise SpeechResponseError(f"transform failed: {exc}") from exc
        if not isinstance(reply, str):
            raise SpeechResponseError("transform must return a string")
        reply = require_text(reply)
        spoken = self.tts.synthesize(reply, **kwargs.get("tts_kwargs", {}))
        return SpeechExchange(
            transcript=transcript,
            reply_text=reply,
            audio=spoken.audio,
            engine=self.NAME,
            metadata={
                "stt": getattr(self.stt, "NAME", type(self.stt).__name__),
                "tts": getattr(self.tts, "NAME", type(self.tts).__name__),
                "synthesis": spoken.to_dict(),
            },
        )
