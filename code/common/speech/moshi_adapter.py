"""Kyutai Moshi style full-duplex frame loop.

Moshi consumes a PCM frame and returns a PCM frame. This adapter does that
loop and nothing else: pass ``engine(frame) -> frame`` already loaded with
weights. Importing ``moshi`` or downloading checkpoints is intentionally not
done here, because a silent download would violate the "no fabricated and
no surprise network" rule used by the other adapters.
"""

# pylint: disable=attribute-defined-outside-init  # adapters set their backend state in initialize(), as in the LLM adapters

from typing import Any, Callable, Dict, List, Optional, Sequence

from ai_platform.common.speech.base import SpeechAdapter
from ai_platform.common.speech.checks import require_audio
from ai_platform.common.speech.models import AudioBuffer, SpeechExchange, Transcript
from ai_platform.common.speech.speech_exception import SpeechConfigError, SpeechResponseError


def split_frames(samples: Sequence[float], frame_size: int) -> List[List[float]]:
    """Pad the tail with zeros so every frame has ``frame_size`` samples."""
    if frame_size <= 0:
        raise SpeechConfigError("frame_size must be positive")
    if not samples:
        raise SpeechResponseError("audio is empty")
    padded = [float(s) for s in samples]
    remainder = len(padded) % frame_size
    if remainder:
        padded.extend([0.0] * (frame_size - remainder))
    return [padded[i:i + frame_size] for i in range(0, len(padded), frame_size)]


class MoshiAdapter(SpeechAdapter):
    """Registry name: ``moshi``."""

    NAME = "moshi"
    CAPABILITIES = frozenset({"sts"})

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        SpeechAdapter.initialize(self, config)
        engine = self.config.get("engine")
        if not callable(engine):
            self.ready = False
            raise SpeechConfigError(
                "MoshiAdapter requires config['engine'] (callable frame -> frame). "
                "Load Kyutai Moshi weights yourself and pass the step function; "
                "this adapter does not download them."
            )
        self.engine: Callable = engine
        self.frame_size = int(self.config.get("frame_size", 1920))
        self.sample_rate = int(self.config.get("sample_rate", 24000))

    def converse(self, audio, **kwargs) -> SpeechExchange:
        self._require_ready()
        buffer = require_audio(audio)
        frames = split_frames(buffer.samples, self.frame_size)
        rendered: List[float] = []
        for frame in frames:
            produced = self.engine(frame)
            if produced is None or len(produced) != len(frame):
                raise SpeechResponseError(
                    "moshi engine must return a frame of the same length as its input"
                )
            rendered.extend(float(s) for s in produced)
        return SpeechExchange(
            transcript=Transcript(text="", engine=self.NAME, duration=buffer.duration),
            reply_text="",
            audio=AudioBuffer(tuple(rendered), buffer.sample_rate),
            engine=self.NAME,
            metadata={"frames": len(frames), "frame_size": self.frame_size,
                      "configured_sample_rate": self.sample_rate},
        )
