"""Gemini Live request/response fragment, transport injected.

Client messages follow the Live API shape closely enough to test and to
hand to a real socket later: ``setup``, then ``realtimeInput.mediaChunks``.
Server messages are read from ``serverContent`` (inline PCM) and
``inputTranscription`` / ``outputTranscription``. No socket is opened here.
"""

# pylint: disable=attribute-defined-outside-init  # adapters set their backend state in initialize(), as in the LLM adapters

from typing import Any, Dict, List, Optional

from ai_platform.common.speech.audio_io import b64_pcm16, resample_linear, samples_from_b64_pcm16
from ai_platform.common.speech.base import SpeechAdapter
from ai_platform.common.speech.checks import require_audio
from ai_platform.common.speech.models import AudioBuffer, SpeechExchange, Transcript
from ai_platform.common.speech.speech_exception import SpeechConfigError, SpeechResponseError


class GeminiLiveAdapter(SpeechAdapter):
    """Registry name: ``gemini-live``."""

    NAME = "gemini-live"
    CAPABILITIES = frozenset({"sts"})
    TARGET_RATE = 16000

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        SpeechAdapter.initialize(self, config)
        self.transport = self.config.get("transport")
        if self.transport is None or not hasattr(self.transport, "exchange"):
            self.ready = False
            raise SpeechConfigError(
                "GeminiLiveAdapter requires config['transport'] with exchange(messages)->messages"
            )
        self.model = str(self.config.get("model", "gemini-2.0-flash-live"))

    def client_messages(self, audio: AudioBuffer) -> List[Dict[str, Any]]:
        """Messages to send for ``audio`` (setup, then the media chunks)."""
        samples = audio.samples
        if audio.sample_rate != self.TARGET_RATE:
            samples = tuple(resample_linear(samples, audio.sample_rate, self.TARGET_RATE))
        return [
            {"setup": {"model": self.model, "generationConfig": {"responseModalities": ["AUDIO"]}}},
            {"realtimeInput": {"mediaChunks": [{
                "mimeType": f"audio/pcm;rate={self.TARGET_RATE}",
                "data": b64_pcm16(samples),
            }]}},
        ]

    def parse_exchange(self, messages: List[Dict[str, Any]]) -> SpeechExchange:
        """SpeechExchange from the server messages of one turn."""
        heard = ""
        reply_parts: List[str] = []
        pcm: List[float] = []
        for message in messages:
            if "inputTranscription" in message:
                heard = message["inputTranscription"].get("text") or heard
            if "outputTranscription" in message:
                text = message["outputTranscription"].get("text")
                if text:
                    reply_parts.append(text)
            content = message.get("serverContent") or {}
            turn = (content.get("modelTurn") or {})
            for part in turn.get("parts") or []:
                inline = part.get("inlineData") or {}
                if inline.get("data"):
                    pcm.extend(samples_from_b64_pcm16(inline["data"]))
                if part.get("text"):
                    reply_parts.append(part["text"])
        reply = " ".join(reply_parts).strip()
        if not reply and not pcm:
            raise SpeechResponseError("gemini-live returned neither text nor audio")
        audio = AudioBuffer(tuple(pcm), self.TARGET_RATE) if pcm else None
        return SpeechExchange(
            transcript=Transcript(text=heard, engine=self.NAME),
            reply_text=reply,
            audio=audio,
            engine=self.NAME,
            metadata={"messages": len(messages), "model": self.model},
        )

    def converse(self, audio, **kwargs) -> SpeechExchange:
        self._require_ready()
        buffer = require_audio(audio)
        outgoing = self.client_messages(buffer)
        incoming = self.transport.exchange(outgoing)
        if not isinstance(incoming, list):
            raise SpeechResponseError("transport.exchange must return a list of messages")
        return self.parse_exchange(incoming)
