"""pyttsx3, the offline SAPI / NSSpeech / eSpeak bridge.

Pass ``config['engine']`` in tests (an object with ``setProperty``,
``save_to_file``, ``runAndWait``). Otherwise the package is imported.
No waveform is invented if the engine does not write the file.
"""

# pylint: disable=import-outside-toplevel  # optional speech stacks are imported only when the adapter is used
# pylint: disable=attribute-defined-outside-init  # adapters set their backend state in initialize(), as in the LLM adapters

from typing import Any, Dict, Optional

from ai_platform.common.speech.audio_io import remove_quietly, temporary_path
from ai_platform.common.speech.base import SpeechAdapter
from ai_platform.common.speech.checks import require_text
from ai_platform.common.speech.models import AudioBuffer, SynthesisResult
from ai_platform.common.speech.speech_exception import SpeechConfigError, SpeechResponseError


class Pyttsx3Adapter(SpeechAdapter):
    """Registry name: ``pyttsx3``."""

    NAME = "pyttsx3"
    CAPABILITIES = frozenset({"tts"})

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        SpeechAdapter.initialize(self, config)
        engine = self.config.get("engine")
        if engine is None:
            try:
                import pyttsx3
            except ImportError as exc:
                self.ready = False
                raise SpeechConfigError("Pyttsx3Adapter requires: pip install pyttsx3") from exc
            engine = pyttsx3.init()
        self.engine = engine
        rate = self.config.get("rate")
        if rate is not None:
            engine.setProperty("rate", int(rate))
        volume = self.config.get("volume")
        if volume is not None:
            engine.setProperty("volume", float(volume))
        voice = self.config.get("voice")
        if voice is not None:
            engine.setProperty("voice", voice)

    def synthesize(self, text: str, **kwargs) -> SynthesisResult:
        self._require_ready()
        sentence = require_text(text)
        target = kwargs.get("output_path")
        temporary = None  # removed after reading; the audio is returned in memory
        if not target:
            target = temporary_path("pyttsx3-", ".wav")
            temporary = target
        voice = str(kwargs.get("voice", self.config.get("voice", "default")))
        self.engine.save_to_file(sentence, target)
        self.engine.runAndWait()
        try:
            audio = AudioBuffer.read(target)
        except (OSError, EOFError, SpeechResponseError) as exc:
            raise SpeechResponseError(f"pyttsx3 did not write a WAV at {target}") from exc
        finally:
            if temporary:
                remove_quietly(temporary)
        if not audio.samples:
            raise SpeechResponseError("pyttsx3 wrote an empty WAV")
        return SynthesisResult(
            audio=audio, engine=self.NAME, voice=voice, format="wav",
            metadata={"output_path": None if temporary else target},
        )

    def shutdown(self) -> None:
        engine = getattr(self, "engine", None)
        if engine is not None and hasattr(engine, "stop"):
            engine.stop()
        SpeechAdapter.shutdown(self)
