"""PCM and WAV helpers that stay inside the standard library.

Neural stacks are optional. The reference synthesizer, the template
recognizer and the tests have to run without NumPy, SciPy or ffmpeg.
"""

import base64
import io
import os
import tempfile
import math
import struct
import wave
from typing import Iterable, List, Sequence, Tuple, Union


PathLike = Union[str, bytes, bytearray]


def rms(samples: Sequence[float]) -> float:
    """Root-mean-square energy. Empty input is 0."""
    if not samples:
        return 0.0
    return math.sqrt(sum(float(s) * float(s) for s in samples) / len(samples))


def tone(frequency: float, seconds: float, sample_rate: int = 16000,
         amplitude: float = 0.5) -> List[float]:
    """A sine. Used by tests and by callers who enroll template words."""
    count = int(seconds * sample_rate)
    return [
        amplitude * math.sin(2.0 * math.pi * frequency * i / sample_rate)
        for i in range(count)
    ]


def noise(seconds: float, sample_rate: int = 16000, amplitude: float = 0.4,
          seed: int = 1) -> List[float]:
    """Deterministic noise (not cryptographic). Same seed, same signal."""
    count = int(seconds * sample_rate)
    samples = []
    state = seed & 0x7FFFFFFF or 1
    for _ in range(count):
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        samples.append(amplitude * (state / 0x7FFFFFFF * 2.0 - 1.0))
    return samples


def resample_linear(samples: Sequence[float], src_rate: int, dst_rate: int) -> List[float]:
    """Linear resampler. Good enough to feed a 24 kHz realtime API from 16 kHz."""
    if src_rate <= 0 or dst_rate <= 0:
        raise ValueError("sample rates must be positive")
    if src_rate == dst_rate or not samples:
        return [float(s) for s in samples]
    out_len = max(1, int(round(len(samples) * dst_rate / src_rate)))
    if len(samples) == 1:
        return [float(samples[0])] * out_len
    last = len(samples) - 1
    out = []
    for i in range(out_len):
        pos = i * last / (out_len - 1)
        lo = int(pos)
        hi = min(lo + 1, last)
        frac = pos - lo
        out.append(float(samples[lo]) * (1.0 - frac) + float(samples[hi]) * frac)
    return out


def dominant_frequency(samples: Sequence[float], sample_rate: int,
                       fmin: float = 70.0, fmax: float = 400.0,
                       step: float = 1.0) -> float:
    """Frequency with the strongest Goertzel response inside ``[fmin, fmax]``.

    The search is bounded so a vowel's F1 does not hide the fundamental when
    the caller asks only about the pitch range.
    """
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    if len(samples) < 8:
        raise ValueError("audio is too short to estimate a frequency")
    lo = len(samples) // 10
    window = [float(s) for s in samples[lo:len(samples) - lo or None]]
    mean = sum(window) / len(window)
    window = [s - mean for s in window]
    best_f = fmin
    best_p = -1.0
    f = fmin
    while f <= fmax + 1e-9:
        power = _goertzel_power(window, sample_rate, f)
        if power > best_p:
            best_p = power
            best_f = f
        f += step
    return best_f


def _goertzel_power(samples: Sequence[float], sample_rate: int, frequency: float) -> float:
    """Relative power of one frequency bin."""
    omega = 2.0 * math.pi * frequency / sample_rate
    coeff = 2.0 * math.cos(omega)
    s0 = s1 = s2 = 0.0
    for sample in samples:
        s0 = sample + coeff * s1 - s2
        s2 = s1
        s1 = s0
    return s1 * s1 + s2 * s2 - coeff * s1 * s2


def write_wav(path: str, samples: Sequence[float], sample_rate: int) -> None:
    """Write mono 16-bit PCM WAV."""
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    raw = pcm16_bytes(samples)
    # pylint: disable=no-member  # wave.open(..., "wb") returns Wave_write; pylint infers Wave_read
    with wave.open(path, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(int(sample_rate))
        handle.writeframes(raw)


def wav_bytes(samples: Sequence[float], sample_rate: int) -> bytes:
    """WAV file contents, for adapters that post audio or return it inline."""
    buffer = io.BytesIO()
    # pylint: disable=no-member  # see write_wav
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(int(sample_rate))
        handle.writeframes(pcm16_bytes(samples))
    return buffer.getvalue()


def read_wav(source: Union[str, bytes, bytearray, io.BufferedIOBase]) -> Tuple[List[float], int]:
    """Read a WAV file or blob. Stereo is reduced to the first channel."""
    if isinstance(source, (bytes, bytearray)):
        stream = io.BytesIO(source)
        close = False
    elif isinstance(source, str):
        stream = open(source, "rb")  # pylint: disable=consider-using-with  # closed below
        close = True
    else:
        stream = source
        close = False
    try:
        with wave.open(stream, "rb") as handle:
            channels = handle.getnchannels()
            width = handle.getsampwidth()
            rate = handle.getframerate()
            frames = handle.readframes(handle.getnframes())
    finally:
        if close:
            stream.close()
    if width == 2:
        count = len(frames) // 2
        values = struct.unpack("<" + "h" * count, frames[:count * 2])
        scale = 32767.0
    elif width == 1:
        values = [(b - 128) / 128.0 for b in frames]
        scale = 1.0
        channels_note = channels
        samples = list(values)
        if channels_note > 1:
            samples = samples[::channels_note]
        return samples, rate
    else:
        raise ValueError(f"unsupported WAV sample width: {width}")
    samples = [v / scale for v in values]
    if channels > 1:
        samples = samples[::channels]
    return samples, rate


def pcm16_bytes(samples: Iterable[float]) -> bytes:
    """Clip to [-1, 1] and pack little-endian int16."""
    out = bytearray()
    for sample in samples:
        value = float(sample)
        if value > 1.0:
            value = 1.0
        elif value < -1.0:
            value = -1.0
        out += struct.pack("<h", int(round(value * 32767.0)))
    return bytes(out)


def samples_from_pcm16(raw: bytes) -> List[float]:
    """Inverse of ``pcm16_bytes``. A trailing odd byte is ignored."""
    count = len(raw) // 2
    values = struct.unpack("<" + "h" * count, raw[:count * 2])
    return [v / 32767.0 for v in values]


def b64_pcm16(samples: Sequence[float]) -> str:
    """Base64 PCM16, the payload of OpenAI Realtime audio deltas."""
    return base64.b64encode(pcm16_bytes(samples)).decode("ascii")


def samples_from_b64_pcm16(payload: str) -> List[float]:
    """Decode a base64 PCM16 delta."""
    return samples_from_pcm16(base64.b64decode(payload))


def temporary_path(prefix: str, suffix: str) -> str:
    """A new empty file in the temp directory; the caller removes it (``remove_quietly``)."""
    handle, path = tempfile.mkstemp(prefix=prefix, suffix=suffix)
    os.close(handle)
    return path


def remove_quietly(path: str) -> None:
    """Delete a temporary file; a file already gone is fine."""
    try:
        os.remove(path)
    except OSError:
        pass
