"""Rule-based formant synthesizer.

This is a traditional-AI baseline, not a neural model and not a stub: it
builds a waveform whose length tracks the text, whose fundamental tracks
``pitch_hz`` and whose vowels differ in F1/F2. It is the stack that always
runs, so other stacks can be compared against a known signal.

It is not meant to be intelligible. It is meant to be deterministic,
offline and free of weights.
"""

import math
from typing import List

from ai_platform.common.speech.base import SpeechAdapter
from ai_platform.common.speech.checks import require_text
from ai_platform.common.speech.models import AudioBuffer, SynthesisResult
from ai_platform.common.speech.speech_exception import SpeechConfigError

# Vowel: (F1, F2) in Hz, a coarse Polish/English map. Consonants are noise.
_VOWELS = {
    "a": (700, 1200),
    "ą": (650, 1100),
    "e": (500, 1800),
    "ę": (480, 1700),
    "i": (320, 2300),
    "o": (500, 900),
    "ó": (400, 800),
    "u": (350, 750),
    "y": (400, 1900),
}
_VOWEL_MS = 90.0
_CONSONANT_MS = 55.0
_SPACE_MS = 70.0
_OTHER_MS = 30.0


def _envelope(index: int, count: int, fade: int) -> float:
    if fade <= 0:
        return 1.0
    if index < fade:
        return 0.5 - 0.5 * math.cos(math.pi * index / fade)
    if index >= count - fade:
        return 0.5 - 0.5 * math.cos(math.pi * (count - 1 - index) / max(fade, 1))
    return 1.0


def _voiced(duration_ms: float, sample_rate: int, pitch_hz: float,
            formant1: float, formant2: float) -> List[float]:
    count = max(1, int(sample_rate * duration_ms / 1000.0))
    fade = min(int(sample_rate * 0.008), count // 4)
    samples = []
    for i in range(count):
        t = i / float(sample_rate)
        partial = (
            0.62 * math.sin(2.0 * math.pi * pitch_hz * t)
            + 0.24 * math.sin(2.0 * math.pi * formant1 * t)
            + 0.10 * math.sin(2.0 * math.pi * formant2 * t)
        )
        samples.append(0.9 * partial * _envelope(i, count, fade))
    return samples


def _unvoiced(duration_ms: float, sample_rate: int, seed: int) -> List[float]:
    count = max(1, int(sample_rate * duration_ms / 1000.0))
    fade = min(int(sample_rate * 0.004), count // 4)
    state = (seed * 1103515245 + 12345) & 0x7FFFFFFF or 1
    samples = []
    for i in range(count):
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        noise = state / 0x7FFFFFFF * 2.0 - 1.0
        samples.append(0.35 * noise * _envelope(i, count, fade))
    return samples


def synthesize_formants(text: str, sample_rate: int = 16000, pitch_hz: float = 140.0,
                        speed: float = 1.0, max_seconds: float = 30.0) -> List[float]:
    """Render ``text``. Raises ``SpeechConfigError`` when the request is unsafe."""
    if sample_rate < 8000:
        raise SpeechConfigError("reference-tts sample_rate must be >= 8000")
    if speed <= 0:
        raise SpeechConfigError("reference-tts speed must be > 0")
    if not 40.0 <= float(pitch_hz) <= 800.0:
        raise SpeechConfigError("reference-tts pitch_hz must be between 40 and 800")
    estimated = len(text) * (_VOWEL_MS / 1000.0) / speed
    if estimated > max_seconds:
        raise SpeechConfigError(
            f"refusing to synthesize about {estimated:.1f}s (max_seconds={max_seconds})"
        )
    samples: List[float] = []
    for index, char in enumerate(text.lower()):
        if char in _VOWELS:
            f1, f2 = _VOWELS[char]
            samples.extend(_voiced(_VOWEL_MS / speed, sample_rate, pitch_hz, f1, f2))
        elif char.isalpha():
            samples.extend(_unvoiced(_CONSONANT_MS / speed, sample_rate, index + 1 + ord(char)))
        elif char.isspace():
            samples.extend([0.0] * int(sample_rate * (_SPACE_MS / speed) / 1000.0))
        else:
            samples.extend([0.0] * int(sample_rate * (_OTHER_MS / speed) / 1000.0))
    return samples


class ReferenceTTSAdapter(SpeechAdapter):
    """Offline formant TTS. Name in the registry: ``reference-tts``."""

    NAME = "reference-tts"
    CAPABILITIES = frozenset({"tts"})

    def synthesize(self, text: str, **kwargs) -> SynthesisResult:
        self._require_ready()
        sentence = require_text(text)
        sample_rate = int(kwargs.get("sample_rate", self.config.get("sample_rate", 16000)))
        pitch_hz = float(kwargs.get("pitch_hz", self.config.get("pitch_hz", 140.0)))
        speed = float(kwargs.get("speed", self.config.get("speed", 1.0)))
        max_seconds = float(kwargs.get("max_seconds", self.config.get("max_seconds", 30.0)))
        voice = str(kwargs.get("voice", self.config.get("voice", "formant")))
        samples = synthesize_formants(sentence, sample_rate, pitch_hz, speed, max_seconds)
        audio = AudioBuffer(tuple(samples), sample_rate)
        result = SynthesisResult(
            audio=audio, engine=self.NAME, voice=voice, format="wav",
            metadata={"pitch_hz": pitch_hz, "speed": speed, "characters": len(sentence)},
        )
        output_path = kwargs.get("output_path")
        if output_path:
            audio.write(output_path)
            result.metadata["output_path"] = output_path
        return result
