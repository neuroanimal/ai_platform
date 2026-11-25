"""gTTS, Google Translate's speech endpoint. Online, MP3, no PCM.

Tests pass ``factory(text=..., lang=...)`` returning an object with
``write_to_fp``. Without ``allow_network`` the adapter does not import gTTS
and does not call Google.
"""

# pylint: disable=import-outside-toplevel  # optional speech stacks are imported only when the adapter is used
# pylint: disable=attribute-defined-outside-init  # adapters set their backend state in initialize(), as in the LLM adapters

import io
from typing import Any, Dict, Optional

from ai_platform.common.speech.base import SpeechAdapter
from ai_platform.common.speech.checks import require_text
from ai_platform.common.speech.models import AudioBuffer, SynthesisResult
from ai_platform.common.speech.speech_exception import SpeechConfigError, SpeechResponseError


class GTTSAdapter(SpeechAdapter):
    """Registry name: ``gtts``."""

    NAME = "gtts"
    CAPABILITIES = frozenset({"tts"})

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        SpeechAdapter.initialize(self, config)
        self.lang = str(self.config.get("lang", "pl"))
        factory = self.config.get("factory")
        if factory is not None:
            self.factory = factory
            return
        if not self.config.get("allow_network"):
            self.ready = False
            raise SpeechConfigError(
                "GTTSAdapter calls Google Translate; set allow_network=True or pass factory="
            )
        try:
            from gtts import gTTS
        except ImportError as exc:
            self.ready = False
            raise SpeechConfigError("GTTSAdapter requires: pip install gTTS") from exc
        self.factory = gTTS

    def synthesize(self, text: str, **kwargs) -> SynthesisResult:
        self._require_ready()
        sentence = require_text(text)
        lang = str(kwargs.get("lang", self.lang))
        engine = self.factory(text=sentence, lang=lang)
        buffer = io.BytesIO()
        engine.write_to_fp(buffer)
        raw = buffer.getvalue()
        if not raw:
            raise SpeechResponseError("gTTS returned no audio")
        audio = AudioBuffer((), 24000)
        result = SynthesisResult(
            audio=audio, engine=self.NAME, voice=lang, format="mp3", raw=raw,
            metadata={"lang": lang, "pcm": False},
        )
        if kwargs.get("output_path"):
            with open(kwargs["output_path"], "wb") as handle:
                handle.write(raw)
            result.metadata["output_path"] = kwargs["output_path"]
        return result
