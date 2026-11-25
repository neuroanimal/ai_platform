"""Value types exchanged by TTS, STT and STS adapters.

Adapters return these objects. They do not return status strings or invented
transcripts: if a backend has no audio or no text, it raises.
"""

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from ai_platform.common.speech.audio_io import read_wav, wav_bytes, write_wav
from ai_platform.common.speech.speech_exception import SpeechResponseError


def _finite_samples(samples: Sequence[Any]) -> Tuple[float, ...]:
    out = []
    for sample in samples:
        try:
            value = float(sample)
        except (TypeError, ValueError) as exc:
            raise SpeechResponseError("audio sample is not a number") from exc
        if not math.isfinite(value):
            raise SpeechResponseError("audio sample is not finite")
        out.append(value)
    return tuple(out)


@dataclass
class AudioBuffer:
    """Mono PCM in ``[-1, 1]`` (values outside the range are clipped on write)."""

    samples: Tuple[float, ...]
    sample_rate: int
    channels: int = 1

    def __post_init__(self) -> None:
        self.samples = _finite_samples(self.samples)
        if self.channels != 1:
            raise SpeechResponseError("only mono audio is supported")
        if int(self.sample_rate) < 0:
            raise SpeechResponseError("sample_rate must be >= 0")
        self.sample_rate = int(self.sample_rate)

    @property
    def duration(self) -> float:
        """Seconds. An empty buffer, or a buffer with no rate, lasts 0."""
        if self.sample_rate <= 0:
            return 0.0
        return len(self.samples) / float(self.sample_rate)

    def write(self, path: str) -> str:
        """Write 16-bit WAV. Returns ``path``."""
        if self.sample_rate <= 0:
            raise SpeechResponseError("cannot write WAV without a sample rate")
        write_wav(path, self.samples, self.sample_rate)
        return path

    def to_wav_bytes(self) -> bytes:
        """In-memory WAV."""
        if self.sample_rate <= 0:
            raise SpeechResponseError("cannot encode WAV without a sample rate")
        return wav_bytes(self.samples, self.sample_rate)

    @classmethod
    def read(cls, path: str) -> "AudioBuffer":
        """Read a WAV file from disk."""
        samples, rate = read_wav(path)
        return cls(tuple(samples), rate)

    @classmethod
    def from_wav_bytes(cls, blob: bytes) -> "AudioBuffer":
        """Read a WAV blob (the body of an HTTP audio response)."""
        samples, rate = read_wav(blob)
        return cls(tuple(samples), rate)

    @classmethod
    def coerce(cls, audio: Union["AudioBuffer", str, bytes, bytearray, Dict[str, Any], Tuple]
               ) -> "AudioBuffer":
        """Accept a buffer, a filesystem path, WAV bytes, ``(samples, rate)`` or a dict."""
        if isinstance(audio, AudioBuffer):
            return audio
        if isinstance(audio, str):
            return cls.read(audio)
        if isinstance(audio, (bytes, bytearray)):
            return cls.from_wav_bytes(bytes(audio))
        if isinstance(audio, tuple) and len(audio) == 2:
            samples, rate = audio
            return cls(tuple(samples), int(rate))
        if isinstance(audio, dict) and "samples" in audio and "sample_rate" in audio:
            return cls(tuple(audio["samples"]), int(audio["sample_rate"]))
        raise SpeechResponseError(
            "audio must be an AudioBuffer, WAV path, WAV bytes, (samples, rate) or a dict"
        )


@dataclass
class Transcript:
    """What an STT adapter heard."""

    text: str
    engine: str
    language: Optional[str] = None
    confidence: Optional[float] = None
    segments: List[Dict[str, Any]] = field(default_factory=list)
    duration: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializable form."""
        return {
            "text": self.text,
            "engine": self.engine,
            "language": self.language,
            "confidence": self.confidence,
            "segments": list(self.segments),
            "duration": self.duration,
        }


@dataclass
class SynthesisResult:
    """What a TTS adapter produced.

    ``audio.samples`` is populated for PCM engines. Compressed engines (MP3
    from edge-tts or gTTS) leave ``samples`` empty and put the file bytes in
    ``raw``; ``format`` says which. Nothing here is a fake waveform.
    """

    audio: AudioBuffer
    engine: str
    voice: str
    format: str = "wav"
    raw: bytes = b""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serializable form."""
        return {
            "engine": self.engine,
            "voice": self.voice,
            "format": self.format,
            "sample_rate": self.audio.sample_rate,
            "duration": self.audio.duration,
            "pcm": bool(self.audio.samples),
            "metadata": dict(self.metadata),
        }


@dataclass
class SpeechExchange:
    """One STS turn: what was heard, what was said back, and the spoken audio."""

    transcript: Transcript
    reply_text: str
    audio: Optional[AudioBuffer]
    engine: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serializable form."""
        return {
            "engine": self.engine,
            "transcript": self.transcript.to_dict(),
            "reply_text": self.reply_text,
            "duration": None if self.audio is None else self.audio.duration,
            "sample_rate": None if self.audio is None else self.audio.sample_rate,
            "metadata": dict(self.metadata),
        }
