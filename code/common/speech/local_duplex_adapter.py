"""Turn-based local duplex: energy VAD, then the same cascade as ``CascadeSTSAdapter``.

"Duplex" here means the adapter finds the speech inside a buffer that also
contains silence, instead of assuming the whole buffer is one utterance.
It is not full-duplex audio like Moshi; that stack has its own adapter.
"""

# pylint: disable=attribute-defined-outside-init  # adapters set their backend state in initialize(), as in the LLM adapters

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ai_platform.common.speech.base import SpeechAdapter
from ai_platform.common.speech.cascade_sts_adapter import CascadeSTSAdapter
from ai_platform.common.speech.checks import require_audio
from ai_platform.common.speech.models import AudioBuffer, SpeechExchange
from ai_platform.common.speech.speech_exception import SpeechConfigError, SpeechResponseError


def speech_regions(samples: Sequence[float], sample_rate: int, frame_ms: float = 20.0,  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
                   threshold: float = 0.02, min_speech_ms: float = 40.0,
                   silence_ms: float = 200.0) -> List[Tuple[int, int]]:
    """Sample ranges whose frame RMS stays above ``threshold``.

    A short dip under the threshold (shorter than ``silence_ms``) does not
    end the region. Regions shorter than ``min_speech_ms`` are dropped.
    """
    if sample_rate <= 0:
        raise SpeechConfigError("sample_rate must be positive")
    frame = max(1, int(sample_rate * frame_ms / 1000.0))
    min_frames = max(1, int(math.ceil(min_speech_ms / frame_ms)))
    silence_frames = max(1, int(math.ceil(silence_ms / frame_ms)))
    voiced = []
    for start in range(0, max(0, len(samples) - frame + 1), frame):
        chunk = samples[start:start + frame]
        energy = math.sqrt(sum(float(s) * float(s) for s in chunk) / float(frame))
        voiced.append(energy >= threshold)
    regions = []
    start_frame = None
    gap = 0
    for index, flag in enumerate(voiced):
        if flag:
            if start_frame is None:
                start_frame = index
            gap = 0
        elif start_frame is not None:
            gap += 1
            if gap >= silence_frames:
                end_frame = index - gap + 1
                if end_frame - start_frame >= min_frames:
                    regions.append((start_frame * frame, min(len(samples), end_frame * frame)))
                start_frame = None
                gap = 0
    if start_frame is not None and len(voiced) - start_frame >= min_frames:
        regions.append((start_frame * frame, len(samples)))
    return regions


def _concat(samples: Sequence[float], regions: Sequence[Tuple[int, int]]) -> List[float]:
    out: List[float] = []
    for start, end in regions:
        out.extend(samples[start:end])
    return out


class LocalDuplexAdapter(SpeechAdapter):
    """Registry name: ``local-duplex``."""

    NAME = "local-duplex"
    CAPABILITIES = frozenset({"sts"})

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        SpeechAdapter.initialize(self, config)
        if self.config.get("stt") is None or self.config.get("tts") is None:
            self.ready = False
            raise SpeechConfigError("LocalDuplexAdapter requires config['stt'] and config['tts']")
        self.cascade = CascadeSTSAdapter()
        self.cascade.initialize({
            "stt": self.config["stt"],
            "tts": self.config["tts"],
            "transform": self.config.get("transform"),
        })
        self.frame_ms = float(self.config.get("frame_ms", 20.0))
        self.threshold = float(self.config.get("threshold", 0.02))
        self.min_speech_ms = float(self.config.get("min_speech_ms", 40.0))
        self.silence_ms = float(self.config.get("silence_ms", 200.0))

    def converse(self, audio, **kwargs) -> SpeechExchange:
        self._require_ready()
        buffer = require_audio(audio)
        regions = speech_regions(
            buffer.samples, buffer.sample_rate, self.frame_ms, self.threshold,
            self.min_speech_ms, self.silence_ms,
        )
        if not regions:
            raise SpeechResponseError("no speech detected")
        speech = _concat(buffer.samples, regions)
        clipped = AudioBuffer(tuple(speech), buffer.sample_rate)
        exchange = self.cascade.converse(clipped, **kwargs)
        exchange.engine = self.NAME
        exchange.metadata["regions"] = [ [start, end] for start, end in regions ]
        exchange.metadata["trimmed_seconds"] = clipped.duration
        return exchange

    def shutdown(self) -> None:
        if getattr(self, "cascade", None) is not None:
            self.cascade.shutdown()
        SpeechAdapter.shutdown(self)
