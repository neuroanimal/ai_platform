
import tempfile
from pathlib import Path

import numpy as np
import torch
import scipy
from scipy import signal
from scipy.io import wavfile

print("=== VERSIONS ===")
print("NumPy:", np.__version__)
print("SciPy:", scipy.__version__)
print("PyTorch:", torch.__version__)

print("\n=== SIGNAL GENERATION ===")

sample_rate = 16000
duration = 2.0

t = np.arange(int(sample_rate * duration)) / sample_rate

audio = (
    0.6 * np.sin(2 * np.pi * 440 * t)
    + 0.3 * np.sin(2 * np.pi * 880 * t)
).astype(np.float32)

assert audio.shape == (32000,)
assert np.isfinite(audio).all()

print("Samples:", len(audio))
print("Duration:", len(audio) / sample_rate)
print("RMS:", float(np.sqrt(np.mean(audio ** 2))))

print("\n=== FFT ===")

spectrum = np.abs(np.fft.rfft(audio))
frequencies = np.fft.rfftfreq(len(audio), 1 / sample_rate)

peak_frequency = frequencies[np.argmax(spectrum)]

assert abs(peak_frequency - 440) < 2

print("Dominant frequency:", peak_frequency)

print("\n=== STFT ===")

frequencies_stft, times_stft, zxx = signal.stft(
    audio,
    fs=sample_rate,
    nperseg=512,
    noverlap=256,
)

assert zxx.ndim == 2
assert np.isfinite(zxx).all()

print("STFT shape:", zxx.shape)

print("\n=== FILTERING ===")

sos = signal.butter(
    4,
    600,
    btype="lowpass",
    fs=sample_rate,
    output="sos",
)

filtered = signal.sosfilt(sos, audio)

assert filtered.shape == audio.shape
assert np.isfinite(filtered).all()

print("Filtered signal:", filtered.shape)

print("\n=== RESAMPLING ===")

resampled = signal.resample_poly(audio, 1, 2)

assert len(resampled) == 16000

print("Resampled:", len(resampled), "samples")
print("New sample rate:", sample_rate // 2)

print("\n=== AUDIO FEATURES ===")

frame_length = 400
hop_length = 160

frames = np.lib.stride_tricks.sliding_window_view(
    audio,
    frame_length,
)[::hop_length]

rms = np.sqrt(np.mean(frames ** 2, axis=1))
zero_crossings = np.mean(
    np.diff(np.signbit(frames), axis=1),
    axis=1,
)

assert len(rms) == len(zero_crossings)
assert np.isfinite(rms).all()

print("Frames:", len(frames))
print("Mean RMS:", float(rms.mean()))
print("Mean zero crossing rate:", float(zero_crossings.mean()))

print("\n=== WAV READ / WRITE ===")

with tempfile.TemporaryDirectory() as tmp:
    wav_path = Path(tmp) / "audio_test.wav"

    wavfile.write(wav_path, sample_rate, audio)

    loaded_rate, loaded_audio = wavfile.read(wav_path)

    assert loaded_rate == sample_rate
    assert loaded_audio.shape == audio.shape

print("WAV roundtrip: PASSED")

print("\n=== PYTORCH AUDIO TENSOR ===")

audio_tensor = torch.from_numpy(audio.copy())

window = torch.hann_window(400)

stft = torch.stft(
    audio_tensor,
    n_fft=512,
    hop_length=160,
    win_length=400,
    window=window,
    return_complex=True,
)

magnitude = stft.abs()

assert magnitude.ndim == 2
assert torch.isfinite(magnitude).all()

print("STFT tensor:", tuple(magnitude.shape))

print("\n=== OPTIONAL SOUNDFILE ===")

try:
    import soundfile as sf

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "soundfile_test.wav"
        sf.write(path, audio, sample_rate)
        loaded, loaded_rate = sf.read(path)

        assert loaded_rate == sample_rate
        assert loaded.shape == audio.shape

    print("SoundFile:", sf.__version__)
    print("SoundFile roundtrip: PASSED")

except ImportError:
    print("SoundFile: NOT INSTALLED - skipped")

print("\nALL AUDIO PROCESSING TESTS PASSED")

