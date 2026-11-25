"""OpenAI Realtime event protocol, transport injected.

The adapter builds the client events (session update, PCM16 append, commit,
response.create) and parses server events (input transcript, audio deltas,
reply transcript). It does not open a WebSocket by itself: pass
``config['transport']`` with ``exchange(events) -> events``. That keeps the
protocol testable and refuses to invent a spoken reply when nothing is connected.
"""

# pylint: disable=attribute-defined-outside-init  # adapters set their backend state in initialize(), as in the LLM adapters

from typing import Any, Dict, List, Optional

from ai_platform.common.speech.audio_io import b64_pcm16, resample_linear, samples_from_b64_pcm16
from ai_platform.common.speech.base import SpeechAdapter
from ai_platform.common.speech.checks import require_audio
from ai_platform.common.speech.models import AudioBuffer, SpeechExchange, Transcript
from ai_platform.common.speech.speech_exception import SpeechConfigError, SpeechResponseError


class OpenAIRealtimeAdapter(SpeechAdapter):
    """Registry name: ``openai-realtime``."""

    NAME = "openai-realtime"
    CAPABILITIES = frozenset({"sts"})
    TARGET_RATE = 24000

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        SpeechAdapter.initialize(self, config)
        self.transport = self.config.get("transport")
        if self.transport is None or not hasattr(self.transport, "exchange"):
            self.ready = False
            raise SpeechConfigError(
                "OpenAIRealtimeAdapter requires config['transport'] with exchange(events)->events"
            )
        self.model = str(self.config.get("model", "gpt-4o-realtime-preview"))
        self.voice = str(self.config.get("voice", "alloy"))

    def session_update(self) -> Dict[str, Any]:
        """The session.update event that configures the realtime session."""
        return {
            "type": "session.update",
            "session": {
                "model": self.model,
                "voice": self.voice,
                "modalities": ["text", "audio"],
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {"model": "whisper-1"},
            },
        }

    def audio_append(self, audio: AudioBuffer) -> Dict[str, Any]:
        """The input_audio_buffer.append event carrying ``audio``."""
        samples = audio.samples
        if audio.sample_rate != self.TARGET_RATE:
            samples = tuple(resample_linear(samples, audio.sample_rate, self.TARGET_RATE))
        return {"type": "input_audio_buffer.append", "audio": b64_pcm16(samples)}

    def client_events(self, audio: AudioBuffer) -> List[Dict[str, Any]]:
        """All client events for one turn with ``audio``."""
        return [
            self.session_update(),
            self.audio_append(audio),
            {"type": "input_audio_buffer.commit"},
            {"type": "response.create"},
        ]

    def parse_exchange(self, events: List[Dict[str, Any]]) -> SpeechExchange:
        """SpeechExchange from the server events of one turn."""
        heard = ""
        reply = ""
        pcm: List[float] = []
        for event in events:
            kind = event.get("type", "")
            if kind == "conversation.item.input_audio_transcription.completed":
                heard = event.get("transcript") or heard
            elif kind in ("response.audio_transcript.done",
                          "response.output_audio_transcript.done"):
                reply = event.get("transcript") or reply
            elif kind in ("response.audio.delta", "response.output_audio.delta"):
                delta = event.get("delta") or ""
                if delta:
                    pcm.extend(samples_from_b64_pcm16(delta))
        if not reply and not pcm:
            raise SpeechResponseError("openai-realtime returned neither text nor audio")
        audio = AudioBuffer(tuple(pcm), self.TARGET_RATE) if pcm else None
        return SpeechExchange(
            transcript=Transcript(text=heard, engine=self.NAME),
            reply_text=reply,
            audio=audio,
            engine=self.NAME,
            metadata={"events": len(events), "model": self.model, "voice": self.voice},
        )

    def converse(self, audio, **kwargs) -> SpeechExchange:
        self._require_ready()
        buffer = require_audio(audio)
        outgoing = self.client_events(buffer)
        incoming = self.transport.exchange(outgoing)
        if not isinstance(incoming, list):
            raise SpeechResponseError("transport.exchange must return a list of events")
        return self.parse_exchange(incoming)
