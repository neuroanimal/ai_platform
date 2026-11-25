"""Kokoro TTS (kokoro-onnx). Local neural voices.

The adapter never downloads a model. Pass ``config['engine']`` whose
``create(text, voice, speed)`` returns ``(samples, sample_rate)``, or pass
``model_path`` and ``voices_path`` so ``kokoro_onnx.Kokoro`` can be constructed.
"""

# pylint: disable=import-outside-toplevel  # optional speech stacks are imported only when the adapter is used
# pylint: disable=attribute-defined-outside-init  # adapters set their backend state in initialize(), as in the LLM adapters

from typing import Any, Dict, Optional

from ai_platform.common.speech.base import SpeechAdapter
from ai_platform.common.speech.checks import require_text
from ai_platform.common.speech.models import AudioBuffer, SynthesisResult
from ai_platform.common.speech.speech_exception import SpeechConfigError, SpeechResponseError


class KokoroAdapter(SpeechAdapter):
    """Registry name: ``kokoro``."""

    NAME = "kokoro"
    CAPABILITIES = frozenset({"tts"})

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        SpeechAdapter.initialize(self, config)
        engine = self.config.get("engine")
        if engine is None:
            model_path = self.config.get("model_path")
            voices_path = self.config.get("voices_path")
            if not model_path or not voices_path:
                self.ready = False
                raise SpeechConfigError(
                    "KokoroAdapter requires engine= or both model_path and voices_path "
                    "(pip install kokoro-onnx; weights are not downloaded here)"
                )
            try:
                from kokoro_onnx import Kokoro
            except ImportError as exc:
                self.ready = False
                raise SpeechConfigError("KokoroAdapter requires: pip install kokoro-onnx") from exc
            engine = Kokoro(model_path, voices_path)
        self.engine = engine

    def synthesize(self, text: str, **kwargs) -> SynthesisResult:
        self._require_ready()
        sentence = require_text(text)
        voice = str(kwargs.get("voice", self.config.get("voice", "af_heart")))
        speed = float(kwargs.get("speed", self.config.get("speed", 1.0)))
        created = self.engine.create(sentence, voice, speed)
        samples, sample_rate = created[0], int(created[1])
        audio = AudioBuffer(tuple(samples), sample_rate)
        if not audio.samples:
            raise SpeechResponseError("kokoro returned no samples")
        result = SynthesisResult(
            audio=audio, engine=self.NAME, voice=voice, format="wav",
            metadata={"speed": speed},
        )
        if kwargs.get("output_path"):
            audio.write(kwargs["output_path"])
            result.metadata["output_path"] = kwargs["output_path"]
        return result
