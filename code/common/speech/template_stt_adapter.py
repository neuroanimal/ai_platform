"""Closed-set template recognizer.

Traditional baseline for STT: you enroll labeled waveforms, and later audio
is matched by a peak-normalized energy envelope, zero-crossing rate and
duration. It does not pretend to be open-vocabulary. With no enrollment it
refuses to guess.
"""

# pylint: disable=attribute-defined-outside-init  # adapters set their backend state in initialize(), as in the LLM adapters

import math
from typing import Any, Dict, List, Optional, Tuple

from ai_platform.common.speech.audio_io import rms
from ai_platform.common.speech.base import SpeechAdapter
from ai_platform.common.speech.checks import require_audio
from ai_platform.common.speech.models import Transcript
from ai_platform.common.speech.speech_exception import SpeechConfigError

_BINS = 32


def fingerprint(samples, sample_rate: int,  # pylint: disable=too-many-locals
                bins: int = _BINS) -> Tuple[Tuple[float, ...], float, float]:
    """Envelope, zero-crossing rate, duration. Loudness is normalized out."""
    if not samples:
        raise SpeechConfigError("cannot fingerprint empty audio")
    peak = max(abs(float(s)) for s in samples) or 1.0
    norm = [float(s) / peak for s in samples]
    step = len(norm) / float(bins)
    envelope = []
    for i in range(bins):
        start = int(i * step)
        stop = max(start + 1, int((i + 1) * step))
        chunk = norm[start:stop]
        envelope.append(math.sqrt(sum(s * s for s in chunk) / len(chunk)))
    crossings = 0
    for left, right in zip(norm, norm[1:]):
        if (left >= 0.0) != (right >= 0.0):
            crossings += 1
    zcr = crossings / float(max(1, len(norm) - 1))
    duration = len(samples) / float(sample_rate)
    return tuple(envelope), zcr, duration


def feature_distance(left, right) -> float:
    """Euclidean envelope plus weighted zcr and duration."""
    env = math.sqrt(sum((a - b) ** 2 for a, b in zip(left[0], right[0])))
    return env + 2.0 * abs(left[1] - right[1]) + 0.3 * abs(left[2] - right[2])


class TemplateSTTAdapter(SpeechAdapter):
    """Registry name: ``template-stt``."""

    NAME = "template-stt"
    CAPABILITIES = frozenset({"stt"})

    def __init__(self) -> None:
        SpeechAdapter.__init__(self)
        self._templates: List[Tuple[str, tuple]] = []

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        SpeechAdapter.initialize(self, config)
        self.max_distance = self.config.get("max_distance")
        enroll = self.config.get("enroll") or []
        for item in enroll:
            self.enroll(item["label"], item["audio"])

    def enroll(self, label: str, audio) -> None:
        """Remember one example of ``label``. Several examples of one label are allowed."""
        if not isinstance(label, str) or not label.strip():
            raise SpeechConfigError("enrollment label must be non-empty text")
        buffer = require_audio(audio)
        self._templates.append((label.strip(), fingerprint(buffer.samples, buffer.sample_rate)))

    def transcribe(self, audio, **kwargs) -> Transcript:
        self._require_ready()
        if not self._templates:
            raise SpeechConfigError("template-stt has no enrollments")
        buffer = require_audio(audio)
        current = fingerprint(buffer.samples, buffer.sample_rate)
        best_label = None
        best_distance = None
        for label, saved in self._templates:
            distance = feature_distance(current, saved)
            if best_distance is None or distance < best_distance:
                best_label = label
                best_distance = distance
        limit = kwargs.get("max_distance", self.max_distance)
        text = best_label
        if limit is not None and best_distance > float(limit):
            text = ""
        confidence = 1.0 / (1.0 + best_distance)
        return Transcript(
            text=text or "",
            engine=self.NAME,
            confidence=confidence,
            duration=buffer.duration,
            segments=[{
                "label": best_label,
                "distance": best_distance,
                "rms": rms(buffer.samples),
            }],
        )
