"""Explicit catalogue of speech stacks.

Importing this module does not import the adapters. ``register_all`` and
``plugins`` do, and they register by name. Nothing is discovered from disk.
"""

# pylint: disable=import-outside-toplevel  # optional speech stacks are imported only when the adapter is used

from dataclasses import dataclass
from typing import Dict, List, Type

from ai_platform.common.core.interface.plugin_contract import PluginContract
from ai_platform.common.speech.base import SpeechAdapter
from ai_platform.common.speech.speech_registry import SpeechRegistry


@dataclass(frozen=True)
class StackSpec:
    """One swappable implementation."""

    name: str
    kind: str
    family: str
    offline: bool
    needs: str
    summary: str


def adapter_map() -> Dict[str, Type[SpeechAdapter]]:  # pylint: disable=too-many-locals
    """Name to class. Imports are inside the function on purpose."""
    from ai_platform.common.speech.cascade_sts_adapter import CascadeSTSAdapter
    from ai_platform.common.speech.coqui_adapter import CoquiTTSAdapter
    from ai_platform.common.speech.edge_tts_adapter import EdgeTTSAdapter
    from ai_platform.common.speech.espeak_adapter import EspeakAdapter
    from ai_platform.common.speech.faster_whisper_adapter import FasterWhisperAdapter
    from ai_platform.common.speech.festival_adapter import FestivalAdapter
    from ai_platform.common.speech.gemini_live_adapter import GeminiLiveAdapter
    from ai_platform.common.speech.gtts_adapter import GTTSAdapter
    from ai_platform.common.speech.kokoro_adapter import KokoroAdapter
    from ai_platform.common.speech.local_duplex_adapter import LocalDuplexAdapter
    from ai_platform.common.speech.moshi_adapter import MoshiAdapter
    from ai_platform.common.speech.nemo_adapter import NeMoAdapter
    from ai_platform.common.speech.openai_realtime_adapter import OpenAIRealtimeAdapter
    from ai_platform.common.speech.openai_stt_adapter import OpenAISTTAdapter
    from ai_platform.common.speech.openai_tts_adapter import OpenAITTSAdapter
    from ai_platform.common.speech.piper_adapter import PiperAdapter
    from ai_platform.common.speech.pyttsx3_adapter import Pyttsx3Adapter
    from ai_platform.common.speech.reference_tts_adapter import ReferenceTTSAdapter
    from ai_platform.common.speech.silero_tts_adapter import SileroTTSAdapter
    from ai_platform.common.speech.speechrecognition_adapter import SpeechRecognitionAdapter
    from ai_platform.common.speech.template_stt_adapter import TemplateSTTAdapter
    from ai_platform.common.speech.vosk_adapter import VoskAdapter
    from ai_platform.common.speech.wav2vec_adapter import Wav2VecAdapter
    from ai_platform.common.speech.whisper_adapter import WhisperAdapter
    from ai_platform.common.speech.whisper_cpp_adapter import WhisperCppAdapter

    return {
        "reference-tts": ReferenceTTSAdapter,
        "espeak": EspeakAdapter,
        "piper": PiperAdapter,
        "festival": FestivalAdapter,
        "pyttsx3": Pyttsx3Adapter,
        "edge-tts": EdgeTTSAdapter,
        "openai-tts": OpenAITTSAdapter,
        "kokoro": KokoroAdapter,
        "coqui": CoquiTTSAdapter,
        "silero-tts": SileroTTSAdapter,
        "gtts": GTTSAdapter,
        "template-stt": TemplateSTTAdapter,
        "whisper": WhisperAdapter,
        "faster-whisper": FasterWhisperAdapter,
        "whisper-cpp": WhisperCppAdapter,
        "vosk": VoskAdapter,
        "wav2vec2": Wav2VecAdapter,
        "speechrecognition": SpeechRecognitionAdapter,
        "openai-stt": OpenAISTTAdapter,
        "nemo": NeMoAdapter,
        "cascade": CascadeSTSAdapter,
        "local-duplex": LocalDuplexAdapter,
        "openai-realtime": OpenAIRealtimeAdapter,
        "gemini-live": GeminiLiveAdapter,
        "moshi": MoshiAdapter,
    }


def stacks() -> List[StackSpec]:
    """Human-readable description of every registered name. Order matches ``adapter_map``."""
    descriptions = {
        "reference-tts": StackSpec("reference-tts", "tts", "traditional-formant", True,
                                   "stdlib", "Deterministic formant baseline, no weights."),
        "espeak": StackSpec("espeak", "tts", "traditional-formant", True,
                            "binary espeak-ng", "eSpeak NG formant/diphone CLI."),
        "piper": StackSpec("piper", "tts", "neural-local", True,
                           "binary piper + onnx voice", "Local ONNX voices."),
        "festival": StackSpec("festival", "tts", "traditional-concatenative", True,
                              "binary text2wave", "Festival text2wave."),
        "pyttsx3": StackSpec("pyttsx3", "tts", "os-bridge", True,
                             "pip install pyttsx3", "SAPI / NSSpeech / eSpeak via pyttsx3."),
        "edge-tts": StackSpec("edge-tts", "tts", "neural-cloud", False,
                              "pip install edge-tts", "Microsoft neural voices, MP3."),
        "openai-tts": StackSpec("openai-tts", "tts", "neural-cloud", False,
                                "OPENAI_API_KEY or LocalAI base_url",
                                "OpenAI /audio/speech, also OpenAI-compatible servers."),
        "kokoro": StackSpec("kokoro", "tts", "neural-local", True,
                            "pip install kokoro-onnx + weights", "Kokoro ONNX voices."),
        "coqui": StackSpec("coqui", "tts", "neural-local", True,
                           "pip install TTS + model_name", "Coqui TTS API."),
        "silero-tts": StackSpec("silero-tts", "tts", "neural-local", True,
                                "torch hub, opt-in download",
                                "Silero TTS, download only if allowed."),
        "gtts": StackSpec("gtts", "tts", "cloud", False,
                          "pip install gTTS", "Google Translate speech, MP3."),
        "template-stt": StackSpec("template-stt", "stt", "traditional-closed-set", True,
                                  "stdlib", "Enroll labeled waveforms, match features."),
        "whisper": StackSpec("whisper", "stt", "neural-local", True,
                             "pip install openai-whisper + model", "openai-whisper."),
        "faster-whisper": StackSpec("faster-whisper", "stt", "neural-local", True,
                                    "pip install faster-whisper + model", "CTranslate2 Whisper."),
        "whisper-cpp": StackSpec("whisper-cpp", "stt", "neural-local", True,
                                 "whisper.cpp binary + ggml", "whisper.cpp CLI."),
        "vosk": StackSpec("vosk", "stt", "neural-local", True,
                          "pip install vosk + model_path", "Vosk / Kaldi recognizer."),
        "wav2vec2": StackSpec("wav2vec2", "stt", "neural-local", True,
                              "pip install transformers + model", "Wav2Vec2 ASR pipeline."),
        "speechrecognition": StackSpec("speechrecognition", "stt", "library-multi", True,
                                       "pip install SpeechRecognition",
                                       "Sphinx offline by default; network backends are opt-in."),
        "openai-stt": StackSpec("openai-stt", "stt", "neural-cloud", False,
                                "OPENAI_API_KEY or LocalAI base_url",
                                "OpenAI /audio/transcriptions."),
        "nemo": StackSpec("nemo", "stt", "neural-local", True,
                          "pip install nemo_toolkit[asr] + model_name", "NVIDIA NeMo ASR."),
        "cascade": StackSpec("cascade", "sts", "compose", True,
                             "any STT + any TTS + optional text transform",
                             "Recognize, rewrite (LLM or rules), speak."),
        "local-duplex": StackSpec("local-duplex", "sts", "vad-cascade", True,
                                  "energy VAD + cascade",
                                  "Trim silence, then the cascade."),
        "openai-realtime": StackSpec("openai-realtime", "sts", "full-duplex-cloud", False,
                                     "transport.exchange",
                                     "OpenAI Realtime events, no socket opened here."),
        "gemini-live": StackSpec("gemini-live", "sts", "full-duplex-cloud", False,
                                 "transport.exchange",
                                 "Gemini Live messages, no socket opened here."),
        "moshi": StackSpec("moshi", "sts", "full-duplex-local", True,
                           "engine(frame)->frame",
                           "Kyutai-style frame loop. Weights are loaded by the caller."),
    }
    classes = adapter_map()
    missing = [name for name in classes if name not in descriptions]
    extra = [name for name in descriptions if name not in classes]
    if missing or extra:
        raise RuntimeError(f"catalogue drift: missing {missing} extra {extra}")
    return [descriptions[name] for name in classes]


class SpeechPlugin(PluginContract):  # pylint: disable=too-few-public-methods
    """One adapter registered under one name. ``register`` is explicit."""

    def __init__(self, name: str, adapter_class: Type[SpeechAdapter]) -> None:
        self.name = name
        self.adapter_class = adapter_class

    def register(self, registry) -> None:
        registry.register(self.name, self.adapter_class)


def plugins() -> List[SpeechPlugin]:
    """A plugin object per stack, for callers that already hold a registry."""
    return [SpeechPlugin(name, cls) for name, cls in adapter_map().items()]


def register_all(registry: SpeechRegistry) -> SpeechRegistry:
    """Register every stack. Returns the same registry."""
    for plugin in plugins():
        plugin.register(registry)
    return registry
