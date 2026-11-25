"""Coqui TTS (the ``TTS`` package).

Pass ``config['engine']`` with ``tts(text) -> samples`` and
``synthesizer.output_sample_rate``, or ``model_name`` to construct
``TTS.api.TTS``. Checkpoints are loaded only when ``model_name`` is set;
there is no implicit download flag beyond what the TTS library itself does,
so leave ``model_name`` unset unless you mean it.
"""

# pylint: disable=import-outside-toplevel  # optional speech stacks are imported only when the adapter is used
# pylint: disable=attribute-defined-outside-init  # adapters set their backend state in initialize(), as in the LLM adapters

from typing import Any, Dict, Optional

from ai_platform.common.speech.base import SpeechAdapter
from ai_platform.common.speech.checks import require_text
from ai_platform.common.speech.models import AudioBuffer, SynthesisResult
from ai_platform.common.speech.speech_exception import SpeechConfigError, SpeechResponseError


class CoquiTTSAdapter(SpeechAdapter):
    """Registry name: ``coqui``."""

    NAME = "coqui"
    CAPABILITIES = frozenset({"tts"})

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        SpeechAdapter.initialize(self, config)
        engine = self.config.get("engine")
        if engine is None:
            model_name = self.config.get("model_name")
            if not model_name:
                self.ready = False
                raise SpeechConfigError(
                    "CoquiTTSAdapter requires engine= or model_name= "
                    "(pip install TTS; no model is selected by default)"
                )
            try:
                from TTS.api import TTS as Coqui
            except ImportError as exc:
                self.ready = False
                raise SpeechConfigError("CoquiTTSAdapter requires: pip install TTS") from exc
            engine = Coqui(model_name=model_name, gpu=bool(self.config.get("gpu", False)))
        self.engine = engine

    def synthesize(self, text: str, **kwargs) -> SynthesisResult:
        self._require_ready()
        sentence = require_text(text)
        voice = str(kwargs.get("voice", self.config.get("voice", "coqui")))
        samples = self.engine.tts(sentence)
        rate = int(kwargs.get(
            "sample_rate",
            getattr(getattr(self.engine, "synthesizer", None), "output_sample_rate", 22050),
        ))
        audio = AudioBuffer(tuple(samples), rate)
        if not audio.samples:
            raise SpeechResponseError("coqui returned no samples")
        result = SynthesisResult(audio=audio, engine=self.NAME, voice=voice, format="wav")
        if kwargs.get("output_path"):
            audio.write(kwargs["output_path"])
            result.metadata["output_path"] = kwargs["output_path"]
        return result
