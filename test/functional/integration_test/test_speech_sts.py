"""Speech pathway wired through the service and the CLI.

Uses the formant synthesizer and the template recognizer, so the test does
not need a GPU, a weight file or a network.
"""

import json

import pytest

from ai_platform.backend.service_layer.micro.speech.speech_service import (
    SpeechService,
    llm_reply_transform,
)
from ai_platform.backend.ui_layer.cli.speech_cli import main
from ai_platform.common.speech.audio_io import dominant_frequency, tone
from ai_platform.common.speech.local_duplex_adapter import LocalDuplexAdapter
from ai_platform.common.speech.models import AudioBuffer
from ai_platform.common.speech.reference_tts_adapter import ReferenceTTSAdapter
from ai_platform.common.speech.speech_exception import SpeechResponseError
from ai_platform.common.speech.speech_registry import SpeechRegistry
from ai_platform.common.speech.template_stt_adapter import TemplateSTTAdapter


class _LLM:
    """Stand-in for any common.llm adapter: chat() returns a string."""

    def chat(self, messages):
        heard = messages[-1]["content"]
        return "usłyszano " + heard


def _service():
    return SpeechService(SpeechRegistry()).register_defaults()


def test_cascade_roundtrip_reference_and_template():
    service = _service()
    speaker = service.registry.get("reference-tts")
    speaker.initialize({"pitch_hz": 160})
    vowel = speaker.synthesize("o")
    listener = service.registry.get("template-stt")
    listener.initialize({})
    listener.enroll("tak", vowel.audio)
    cascade = service.registry.get("cascade")
    cascade.initialize({
        "stt": listener,
        "tts": speaker,
        "transform": lambda text: "a" if text == "tak" else "e",
    })
    exchange = cascade.converse(vowel.audio)
    assert exchange.transcript.text == "tak"
    assert exchange.reply_text == "a"
    heard_pitch = dominant_frequency(exchange.audio.samples, exchange.audio.sample_rate, 80, 250)
    assert heard_pitch == pytest.approx(160, abs=4)
    assert exchange.metadata["stt"] == "template-stt"
    assert exchange.metadata["tts"] == "reference-tts"


def test_llm_transform_is_a_duck_typed_chat():
    service = _service()
    speaker = ReferenceTTSAdapter()
    speaker.initialize({})
    audio = speaker.synthesize("aaa")
    listener = TemplateSTTAdapter()
    listener.initialize({})
    listener.enroll("aaa", audio.audio)
    cascade = service.registry.get("cascade")
    cascade.initialize({
        "stt": listener,
        "tts": speaker,
        "transform": llm_reply_transform(_LLM()),
    })
    exchange = cascade.converse(audio.audio)
    assert exchange.transcript.text == "aaa"
    assert exchange.reply_text == "usłyszano aaa"
    assert exchange.audio.duration > 0


def test_text_pathway_matches_speech_pathway_when_recognition_is_perfect():
    service = _service()
    report = None
    speaker = service.registry.get("reference-tts")
    speaker.initialize({})
    listener = service.registry.get("template-stt")
    listener.initialize({})
    demo = speaker.synthesize("aaa")
    listener.enroll("aaa", demo.audio)
    report = service.compare_text_and_speech(
        "aaa", listener, speaker, transform=lambda text: text.upper(),
    )
    assert report.input_wer == 0.0
    assert report.text_reply == "AAA"
    assert report.speech_transcript == "aaa"
    assert report.speech_reply == "AAA"
    assert report.reply_wer == 0.0


def test_local_duplex_strips_silence_before_the_cascade():
    seen = {}

    class Listener:
        NAME = "fake-stt"

        def transcribe(self, audio, **kwargs):
            seen["seconds"] = audio.duration
            from ai_platform.common.speech.models import Transcript
            return Transcript(text="tak", engine="fake-stt", duration=audio.duration)

    class Speaker:
        NAME = "fake-tts"

        def synthesize(self, text, **kwargs):
            from ai_platform.common.speech.models import SynthesisResult
            samples = tuple(tone(300, 0.05))
            return SynthesisResult(audio=AudioBuffer(samples, 16000), engine="fake-tts", voice="x")

    duplex = LocalDuplexAdapter()
    duplex.initialize({"stt": Listener(), "tts": Speaker(), "threshold": 0.05, "silence_ms": 80})
    padded = [0.0] * 16000 + tone(440, 0.1, amplitude=0.5) + [0.0] * 16000
    exchange = duplex.converse(AudioBuffer(tuple(padded), 16000))
    assert exchange.reply_text == "tak"
    assert seen["seconds"] < 0.5
    assert exchange.metadata["regions"]
    with pytest.raises(SpeechResponseError, match="no speech"):
        duplex.converse(AudioBuffer(tuple([0.0] * 16000), 16000))


def test_cli_list_tts_stt_sts_and_compare(tmp_path, capsys):
    registry = SpeechRegistry()
    assert main(["list"], registry=registry) == 0
    listed = capsys.readouterr().out
    assert "reference-tts" in listed and "template-stt" in listed and "cascade" in listed

    wav = tmp_path / "a.wav"
    assert main([
        "tts", "--engine", "reference-tts", "--text", "aaa", "--output", str(wav), "--pitch-hz", "150",
    ], registry=SpeechRegistry()) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["engine"] == "reference-tts"
    assert wav.exists() and wav.stat().st_size > 44

    assert main([
        "stt", "--engine", "template-stt", "--input", str(wav), "--enroll", f"aaa={wav}",
    ], registry=SpeechRegistry()) == 0
    heard = json.loads(capsys.readouterr().out)
    assert heard["text"] == "aaa"

    reply = tmp_path / "reply.wav"
    assert main([
        "sts", "--stt", "template-stt", "--tts", "reference-tts",
        "--input", str(wav), "--output", str(reply), "--enroll", f"aaa={wav}", "--uppercase",
    ], registry=SpeechRegistry()) == 0
    exchange = json.loads(capsys.readouterr().out)
    assert exchange["transcript"]["text"] == "aaa"
    assert exchange["reply_text"] == "AAA"
    assert reply.exists()

    assert main([
        "compare", "--text", "aaa", "--bootstrap-template", "--uppercase",
    ], registry=SpeechRegistry()) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["input_wer"] == 0.0
    assert report["speech_reply"] == "AAA"

    assert main(["tts", "--text", "   ", "--output", str(tmp_path / "no.wav")], registry=SpeechRegistry()) == 1
    assert "empty" in capsys.readouterr().err
