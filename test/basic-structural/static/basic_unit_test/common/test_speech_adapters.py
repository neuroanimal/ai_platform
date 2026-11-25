"""Speech adapters. External programs and neural weights are not required.

CLI adapters get a recording runner. HTTP adapters get an opener. Neural
adapters get a fake engine. The formant TTS, template STT, metrics and VAD
run for real.
"""

import json
import os
import shutil

import pytest

from ai_platform.common.core.registry.plugin_registry import PluginRegistry
from ai_platform.common.speech.audio_io import dominant_frequency, noise, read_wav, tone, wav_bytes
from ai_platform.common.speech.catalog import plugins, register_all, stacks
from ai_platform.common.speech.coqui_adapter import CoquiTTSAdapter
from ai_platform.common.speech.edge_tts_adapter import EdgeTTSAdapter
from ai_platform.common.speech.espeak_adapter import EspeakAdapter, espeak_command
from ai_platform.common.speech.evaluation import cer, wer
from ai_platform.common.speech.faster_whisper_adapter import FasterWhisperAdapter
from ai_platform.common.speech.festival_adapter import FestivalAdapter
from ai_platform.common.speech.gemini_live_adapter import GeminiLiveAdapter
from ai_platform.common.speech.gtts_adapter import GTTSAdapter
from ai_platform.common.speech.kokoro_adapter import KokoroAdapter
from ai_platform.common.speech.local_duplex_adapter import speech_regions
from ai_platform.common.speech.models import AudioBuffer
from ai_platform.common.speech.moshi_adapter import MoshiAdapter
from ai_platform.common.speech.nemo_adapter import NeMoAdapter
from ai_platform.common.speech.openai_realtime_adapter import OpenAIRealtimeAdapter
from ai_platform.common.speech.openai_stt_adapter import OpenAISTTAdapter
from ai_platform.common.speech.openai_tts_adapter import OpenAITTSAdapter
from ai_platform.common.speech.piper_adapter import PiperAdapter, piper_command
from ai_platform.common.speech.pyttsx3_adapter import Pyttsx3Adapter
from ai_platform.common.speech.reference_tts_adapter import ReferenceTTSAdapter
from ai_platform.common.speech.silero_tts_adapter import SileroTTSAdapter
from ai_platform.common.speech.speech_exception import (
    SpeechCapabilityError,
    SpeechConfigError,
    SpeechResponseError,
)
from ai_platform.common.speech.speech_registry import SpeechRegistry, get_registry
from ai_platform.common.speech.speechrecognition_adapter import SpeechRecognitionAdapter
from ai_platform.common.speech.template_stt_adapter import TemplateSTTAdapter
from ai_platform.common.speech.vosk_adapter import VoskAdapter
from ai_platform.common.speech.wav2vec_adapter import Wav2VecAdapter
from ai_platform.common.speech.whisper_adapter import WhisperAdapter
from ai_platform.common.speech.whisper_cpp_adapter import WhisperCppAdapter, whisper_cpp_command
from ai_platform.common.tool.validate_dependencies import find_violations
from ai_platform.common.util.cli_runner import ToolResult


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))


class Recorder:
    """Stand-in for run_tool. Writes the WAV or transcript the adapter will read back."""

    def __init__(self):
        self.commands = []
        self.stdins = []

    def __call__(self, command, timeout=None, stdin=None, cwd=None, env=None):
        command = list(command)
        self.commands.append(command)
        self.stdins.append(stdin)
        if "-w" in command:
            _write_tone(command[command.index("-w") + 1])
        if "--output_file" in command:
            _write_tone(command[command.index("--output_file") + 1])
        if "-o" in command:
            _write_tone(command[command.index("-o") + 1])
        if "-of" in command:
            base = command[command.index("-of") + 1]
            with open(base + ".txt", "w", encoding="utf-8") as handle:
                handle.write("rozpoznany tekst\n")
        return ToolResult(command, 0, "", "")


def _write_tone(path):
    AudioBuffer(tuple(tone(440, 0.05, 8000, 0.2)), 8000).write(path)


def _patch_which(monkeypatch):
    monkeypatch.setattr("ai_platform.common.util.cli_runner.shutil.which", lambda name: None)


# ----------------------------------------------------------------------------
# metrics, audio, registry
# ----------------------------------------------------------------------------

def test_wer_and_cer_ignore_case_and_punctuation():
    assert wer("kot pies", "kot") == 0.5
    assert wer("a b", "a b") == 0.0
    assert wer("Kot,", "kot") == 0.0
    assert wer("", "") == 0.0
    assert wer("", "x") == 1.0
    assert cer("kot", "kit") == pytest.approx(1 / 3)


def test_wav_roundtrip_and_coerce(tmp_path):
    original = AudioBuffer((0.0, 0.5, -0.5, 0.25), 8000)
    path = tmp_path / "a.wav"
    original.write(str(path))
    loaded = AudioBuffer.read(str(path))
    assert loaded.sample_rate == 8000
    assert len(loaded.samples) == 4
    assert loaded.samples[1] == pytest.approx(0.5, abs=1 / 100)
    blob = wav_bytes([0.25, -0.25], 16000)
    assert AudioBuffer.coerce(blob).sample_rate == 16000
    assert AudioBuffer.coerce((tone(100, 0.01, 8000), 8000)).duration == pytest.approx(0.01, abs=0.002)


def test_registry_is_explicit_and_plugins_match_the_catalogue():
    registry = SpeechRegistry()
    assert registry.list() == []
    with pytest.raises(ValueError, match="not registered"):
        registry.get("reference-tts")
    register_all(registry)
    described = stacks()
    assert [spec.name for spec in described] == registry.list()
    for spec in described:
        assert spec.kind in registry.get_class(spec.name).CAPABILITIES
    assert get_registry() is get_registry()
    fresh = PluginRegistry()
    for plugin in plugins():
        plugin.register(fresh)
    assert set(fresh.list()) == set(registry.list())


def test_speech_imports_respect_layer_rules():
    violations = [item for item in find_violations(ROOT) if "speech" in item.replace("\\", "/")]
    assert violations == []


# ----------------------------------------------------------------------------
# reference TTS and template STT
# ----------------------------------------------------------------------------

def test_reference_tts_tracks_pitch_speed_and_refuses_garbage():
    adapter = ReferenceTTSAdapter()
    with pytest.raises(SpeechConfigError, match="not initialized"):
        adapter.synthesize("a")
    adapter.initialize({})
    with pytest.raises(SpeechCapabilityError):
        adapter.transcribe(AudioBuffer(tuple(tone(200, 0.1)), 16000))
    with pytest.raises(SpeechResponseError):
        adapter.synthesize("   ")
    low = adapter.synthesize("a" * 8, pitch_hz=120)
    high = adapter.synthesize("a" * 8, pitch_hz=220)
    assert dominant_frequency(low.audio.samples, 16000, 80, 180) == pytest.approx(120, abs=3)
    assert dominant_frequency(high.audio.samples, 16000, 150, 320) == pytest.approx(220, abs=3)
    slow = adapter.synthesize("a" * 10, speed=1)
    fast = adapter.synthesize("a" * 10, speed=2)
    assert len(slow.audio.samples) == 2 * len(fast.audio.samples)
    assert adapter.synthesize("cześć").audio.samples == adapter.synthesize("cześć").audio.samples
    with pytest.raises(SpeechConfigError, match="max_seconds"):
        adapter.synthesize("a" * 5000, max_seconds=1)
    assert max(abs(s) for s in low.audio.samples) <= 1.0


def test_template_stt_matches_enrolled_signals_and_does_not_guess():
    adapter = TemplateSTTAdapter()
    adapter.initialize({})
    with pytest.raises(SpeechConfigError, match="no enroll"):
        adapter.transcribe(AudioBuffer(tuple(tone(200, 0.2)), 16000))
    adapter.enroll("low", AudioBuffer(tuple(tone(200, 0.3)), 16000))
    adapter.enroll("high", AudioBuffer(tuple(tone(900, 0.3)), 16000))
    adapter.enroll("noise", AudioBuffer(tuple(noise(0.3, seed=3)), 16000))
    assert adapter.transcribe(AudioBuffer(tuple(tone(200, 0.3)), 16000)).text == "low"
    assert adapter.transcribe(AudioBuffer(tuple(tone(900, 0.3)), 16000)).text == "high"
    assert adapter.transcribe(AudioBuffer(tuple(noise(0.3, seed=3)), 16000)).text == "noise"
    rejected = adapter.transcribe(AudioBuffer(tuple(tone(200, 0.3)), 16000), max_distance=0.0)
    # identical audio has distance 0, so it is still accepted at the boundary
    assert rejected.text == "low"
    far = adapter.transcribe(
        AudioBuffer(tuple(noise(0.3, seed=9)), 16000), max_distance=0.01,
    )
    assert far.text == ""
    assert far.confidence is not None and far.confidence < 1


def test_vad_drops_silence_and_keeps_a_tone():
    rate = 16000
    samples = [0.0] * rate + tone(440, 0.12, rate, 0.4) + [0.0] * rate
    regions = speech_regions(samples, rate, threshold=0.05, min_speech_ms=40, silence_ms=100)
    assert len(regions) == 1
    start, end = regions[0]
    assert start >= rate - 400
    assert end <= rate + int(0.12 * rate) + 400
    assert speech_regions([0.0] * rate, rate, threshold=0.05) == []


# ----------------------------------------------------------------------------
# CLI stacks
# ----------------------------------------------------------------------------

@pytest.mark.parametrize("cls", [EspeakAdapter, FestivalAdapter])
def test_cli_tts_missing_binary(monkeypatch, cls):
    _patch_which(monkeypatch)
    with pytest.raises(SpeechConfigError, match="not found"):
        cls().initialize({})


def test_espeak_command_keeps_text_off_the_argument_list(tmp_path):
    runner = Recorder()
    adapter = EspeakAdapter()
    adapter.initialize({"executable": "espeak-ng", "runner": runner})
    target = str(tmp_path / "out.wav")
    tricky = "cześć '; rm -rf /"
    result = adapter.synthesize(tricky, output_path=target, voice="pl", wpm=140, pitch=40)
    assert runner.commands == [espeak_command("espeak-ng", target, "pl", 140, 40)]
    assert runner.stdins == [tricky]
    assert "rm" not in runner.commands[0]
    assert result.audio.sample_rate == 8000
    assert result.audio.duration > 0


def test_piper_command_is_one_argv_per_value(tmp_path):
    runner = Recorder()
    adapter = PiperAdapter()
    model = "voices/pl pl;rm.onnx"
    adapter.initialize({"executable": "piper", "runner": runner, "model": model})
    target = str(tmp_path / "out.wav")
    adapter.synthesize("dzień dobry", output_path=target, speaker="0")
    assert runner.commands == [piper_command("piper", model, target, "0")]
    assert runner.stdins == ["dzień dobry"]
    with pytest.raises(SpeechConfigError, match="model"):
        PiperAdapter().initialize({})


def test_whisper_cpp_reads_the_transcript_file(tmp_path):
    runner = Recorder()
    adapter = WhisperCppAdapter()
    adapter.initialize({"executable": "whisper-cli", "runner": runner, "model": "ggml.bin"})
    audio = AudioBuffer(tuple(tone(200, 0.05)), 16000)
    transcript = adapter.transcribe(audio, language="pl")
    assert transcript.text == "rozpoznany tekst"
    command = runner.commands[0]
    assert command[:3] == ["whisper-cli", "-m", "ggml.bin"]
    assert "-otxt" in command and "-l" in command and "pl" in command
    assert command == whisper_cpp_command(
        "whisper-cli", "ggml.bin", command[command.index("-f") + 1],
        command[command.index("-of") + 1], "pl",
    )
    with pytest.raises(SpeechConfigError, match="model"):
        WhisperCppAdapter().initialize({})


# ----------------------------------------------------------------------------
# injected engines and HTTP
# ----------------------------------------------------------------------------

def test_pyttsx3_edge_and_gtts_use_the_injected_backend(tmp_path):
    class Engine:
        def __init__(self):
            self.saved = None

        def setProperty(self, key, value):
            return None

        def save_to_file(self, text, path):
            self.saved = (text, path)

        def runAndWait(self):
            AudioBuffer(tuple(tone(330, 0.05, 16000)), 16000).write(self.saved[1])

        def stop(self):
            return None

    py = Pyttsx3Adapter()
    py.initialize({"engine": Engine(), "rate": 180})
    spoken = py.synthesize("halo", output_path=str(tmp_path / "py.wav"))
    assert spoken.audio.duration > 0
    py.shutdown()

    def fake_edge(text, voice, rate, pitch, path):
        assert text == "halo" and voice.startswith("pl-")
        with open(path, "wb") as handle:
            handle.write(b"ID3not-really")

    edge = EdgeTTSAdapter()
    edge.initialize({"synthesize": fake_edge})
    mp3 = edge.synthesize("halo")
    assert mp3.format == "mp3" and mp3.raw.startswith(b"ID3") and mp3.audio.samples == ()

    class FakeGTTS:
        def __init__(self, text, lang):
            self.payload = f"{lang}:{text}".encode("utf-8")

        def write_to_fp(self, buffer):
            buffer.write(self.payload)

    gtts = GTTSAdapter()
    gtts.initialize({"factory": FakeGTTS, "lang": "pl"})
    result = gtts.synthesize("cześć")
    assert result.raw == "pl:cześć".encode("utf-8")
    with pytest.raises(SpeechConfigError, match="allow_network"):
        GTTSAdapter().initialize({})


def test_neural_tts_engines_return_their_samples():
    class Kokoro:
        def create(self, text, voice, speed):
            return tone(180, 0.05), 16000

    kokoro = KokoroAdapter()
    kokoro.initialize({"engine": Kokoro()})
    assert kokoro.synthesize("a", voice="af_heart").audio.sample_rate == 16000

    class Coqui:
        def tts(self, text):
            return tone(200, 0.05, 22050)

    coqui = CoquiTTSAdapter()
    coqui.initialize({"engine": Coqui()})
    assert coqui.synthesize("a").audio.sample_rate == 22050

    class Silero:
        def apply_tts(self, text, speaker, sample_rate):
            return tone(150, 0.05, sample_rate)

    silero = SileroTTSAdapter()
    silero.initialize({"engine": Silero()})
    assert len(silero.synthesize("a", voice="pl_female").audio.samples) > 0
    with pytest.raises(SpeechConfigError, match="download"):
        SileroTTSAdapter().initialize({})
    with pytest.raises(SpeechConfigError, match="model_path"):
        KokoroAdapter().initialize({})
    with pytest.raises(SpeechConfigError, match="model_name"):
        CoquiTTSAdapter().initialize({})


def test_optional_import_hint(monkeypatch):
    real = __import__

    def blocked(name, globals=None, locals=None, fromlist=(), level=0):
        if name in {"whisper", "pyttsx3", "nemo.collections.asr"} or name.startswith("nemo"):
            raise ImportError(name)
        return real(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", blocked)
    with pytest.raises(SpeechConfigError, match="openai-whisper"):
        WhisperAdapter().initialize({"model": "tiny"})
    with pytest.raises(SpeechConfigError, match="pyttsx3"):
        Pyttsx3Adapter().initialize({})
    with pytest.raises(SpeechConfigError, match="nemo_toolkit"):
        NeMoAdapter().initialize({"model_name": "stt_pl"})


def test_stt_engines_read_what_the_fake_model_returns(tmp_path):
    class Whisper:
        def transcribe(self, path, **kwargs):
            assert os.path.exists(path)
            return {"text": " tak ", "language": "pl", "segments": [{"text": "tak"}]}

    whisper = WhisperAdapter()
    whisper.initialize({"engine": Whisper()})
    heard = whisper.transcribe(AudioBuffer(tuple(tone(200, 0.05)), 16000))
    assert heard.text == "tak" and heard.language == "pl"
    with pytest.raises(SpeechConfigError, match="model"):
        WhisperAdapter().initialize({})

    class Segment:
        def __init__(self, text):
            self.text = text
            self.start = 0.0
            self.end = 0.1

    class Info:
        language = "pl"
        language_probability = 0.9

    class Faster:
        def transcribe(self, path, language=None):
            return [Segment("dzień"), Segment("dobry")], Info()

    faster = FasterWhisperAdapter()
    faster.initialize({"engine": Faster()})
    assert faster.transcribe(AudioBuffer(tuple(tone(200, 0.05)), 16000)).text == "dzień dobry"

    class Vosk:
        def AcceptWaveform(self, pcm):
            assert pcm[:4]
            return 1

        def Result(self):
            return json.dumps({"text": "tak"})

    vosk = VoskAdapter()
    vosk.initialize({"recognizer": Vosk()})
    assert vosk.transcribe(AudioBuffer(tuple(tone(200, 0.05)), 16000)).text == "tak"
    with pytest.raises(SpeechConfigError, match="model_path"):
        VoskAdapter().initialize({})

    wav2vec = Wav2VecAdapter()
    wav2vec.initialize({"engine": lambda path: {"text": "ok"}})
    assert wav2vec.transcribe(AudioBuffer(tuple(tone(200, 0.05)), 16000)).text == "ok"

    nemo = NeMoAdapter()
    nemo.initialize({"engine": type("N", (), {"transcribe": lambda self, paths: ["halo"]})()})
    assert nemo.transcribe(AudioBuffer(tuple(tone(200, 0.05)), 16000)).text == "halo"

    sr = SpeechRecognitionAdapter()
    sr.initialize({"recognize": lambda path: "sphinx-ok"})
    assert sr.transcribe(AudioBuffer(tuple(tone(200, 0.05)), 16000)).text == "sphinx-ok"
    with pytest.raises(SpeechConfigError, match="allow_network"):
        SpeechRecognitionAdapter().initialize({"backend": "google"})


def _opener_tts(request, timeout):
    assert request.get_header("Authorization") == "Bearer secret"
    assert request.full_url.endswith("/audio/speech")
    body = json.loads(request.data.decode("utf-8"))
    assert body["input"] == "cześć" and body["voice"] == "alloy"
    return 200, wav_bytes(tone(440, 0.02, 16000, 0.2), 16000)


def _opener_stt(request, timeout):
    assert request.get_header("Authorization") == "Bearer secret"
    assert b'name="model"' in request.data
    assert b"audio.wav" in request.data
    return 200, json.dumps({"text": "tak", "language": "pl"}).encode("utf-8")


def test_openai_compatible_audio_http(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(SpeechConfigError, match="api_key"):
        OpenAITTSAdapter().initialize({})
    speaker = OpenAITTSAdapter()
    speaker.initialize({
        "api_key": "secret", "opener": _opener_tts,
        "base_url": "http://127.0.0.1:8081/v1",
    })
    spoken = speaker.synthesize("cześć")
    assert spoken.audio.sample_rate == 16000 and spoken.format == "wav"

    def failing(request, timeout):
        return 503, b"overloaded"

    broken = OpenAITTSAdapter()
    broken.initialize({"api_key": "secret", "opener": failing})
    with pytest.raises(SpeechResponseError, match="HTTP 503"):
        broken.synthesize("a")

    listener = OpenAISTTAdapter()
    listener.initialize({"api_key": "secret", "opener": _opener_stt, "model": "whisper-1"})
    heard = listener.transcribe(AudioBuffer(tuple(tone(200, 0.05)), 16000), language="pl")
    assert heard.text == "tak"


def test_realtime_and_gemini_and_moshi_do_not_open_sockets():
    with pytest.raises(SpeechConfigError, match="transport"):
        OpenAIRealtimeAdapter().initialize({})
    seen = {}

    def exchange(events):
        seen["events"] = events
        from ai_platform.common.speech.audio_io import b64_pcm16
        return [
            {"type": "conversation.item.input_audio_transcription.completed", "transcript": "cześć"},
            {"type": "response.audio_transcript.done", "transcript": "dzień dobry"},
            {"type": "response.audio.delta", "delta": b64_pcm16([0.1, -0.2, 0.3, -0.4])},
            {"type": "response.done"},
        ]

    realtime = OpenAIRealtimeAdapter()
    realtime.initialize({"transport": type("T", (), {"exchange": staticmethod(exchange)})()})
    turn = realtime.converse(AudioBuffer(tuple(tone(220, 0.05)), 16000))
    assert turn.transcript.text == "cześć"
    assert turn.reply_text == "dzień dobry"
    assert len(turn.audio.samples) == 4
    assert [event["type"] for event in seen["events"]] == [
        "session.update", "input_audio_buffer.append", "input_audio_buffer.commit", "response.create",
    ]

    def gemini_exchange(messages):
        from ai_platform.common.speech.audio_io import b64_pcm16
        assert messages[0]["setup"]["model"].startswith("gemini")
        return [
            {"inputTranscription": {"text": "hej"}},
            {"serverContent": {"modelTurn": {"parts": [
                {"inlineData": {"mimeType": "audio/pcm;rate=16000", "data": b64_pcm16([0.2, -0.2])}},
                {"text": "cześć"},
            ]}}},
        ]

    gemini = GeminiLiveAdapter()
    gemini.initialize({"transport": type("T", (), {"exchange": staticmethod(gemini_exchange)})()})
    live = gemini.converse(AudioBuffer(tuple(tone(180, 0.05)), 16000))
    assert live.transcript.text == "hej" and live.reply_text == "cześć"
    assert len(live.audio.samples) == 2

    def invert(frame):
        return [-sample for sample in frame]

    moshi = MoshiAdapter()
    moshi.initialize({"engine": invert, "frame_size": 4, "sample_rate": 16000})
    reply = moshi.converse(AudioBuffer((0.1, -0.2, 0.3, -0.4, 0.5), 16000))
    assert reply.audio.samples[:5] == pytest.approx((-0.1, 0.2, -0.3, 0.4, -0.5))
    assert len(reply.audio.samples) == 8  # padded to a whole frame
    with pytest.raises(SpeechConfigError, match="engine"):
        MoshiAdapter().initialize({})


def test_shutil_still_importable():
    """The which-patch above is per-test; this only documents the import used by CLI adapters."""
    assert shutil.which("python3") or shutil.which("python")
