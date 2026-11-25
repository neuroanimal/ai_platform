"""Silero TTS (torch.hub snippet in the docstring, not executed here).

Weights are not downloaded unless ``allow_download`` is true. Tests and
offline use pass ``engine`` with ``apply_tts(text, speaker, sample_rate)``.

Real load, when you opt in::

    import torch
    engine, _ = torch.hub.load(
        repo_or_dir="snakers4/silero-models", model="silero_tts",
        language="pl", speaker="v3_pl",
    )
"""

# pylint: disable=import-outside-toplevel  # optional speech stacks are imported only when the adapter is used
# pylint: disable=attribute-defined-outside-init  # adapters set their backend state in initialize(), as in the LLM adapters

from typing import Any, Dict, Optional

from ai_platform.common.speech.base import SpeechAdapter
from ai_platform.common.speech.checks import require_text
from ai_platform.common.speech.models import AudioBuffer, SynthesisResult
from ai_platform.common.speech.speech_exception import SpeechConfigError, SpeechResponseError


class SileroTTSAdapter(SpeechAdapter):
    """Registry name: ``silero-tts``."""

    NAME = "silero-tts"
    CAPABILITIES = frozenset({"tts"})

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        SpeechAdapter.initialize(self, config)
        engine = self.config.get("engine")
        if engine is None:
            if not self.config.get("allow_download"):
                self.ready = False
                raise SpeechConfigError(
                    "SileroTTSAdapter refuses to download weights; "
                    "pass engine= or set allow_download=True"
                )
            try:
                import torch
            except ImportError as exc:
                self.ready = False
                raise SpeechConfigError("SileroTTSAdapter requires: pip install torch") from exc
            language = self.config.get("language", "pl")
            speaker = self.config.get("speaker_model", "v3_pl")
            engine, _ = torch.hub.load(
                repo_or_dir="snakers4/silero-models", model="silero_tts",
                language=language, speaker=speaker,
            )
        self.engine = engine

    def synthesize(self, text: str, **kwargs) -> SynthesisResult:
        self._require_ready()
        sentence = require_text(text)
        speaker = str(kwargs.get("voice", self.config.get("voice", "pl_female")))
        sample_rate = int(kwargs.get("sample_rate", self.config.get("sample_rate", 16000)))
        produced = self.engine.apply_tts(sentence, speaker, sample_rate)
        audio = AudioBuffer(tuple(produced), sample_rate)
        if not audio.samples:
            raise SpeechResponseError("silero returned no samples")
        result = SynthesisResult(audio=audio, engine=self.NAME, voice=speaker, format="wav",
                                 metadata={"sample_rate": sample_rate})
        if kwargs.get("output_path"):
            audio.write(kwargs["output_path"])
        return result
