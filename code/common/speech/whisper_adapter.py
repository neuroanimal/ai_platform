"""openai-whisper.

Pass ``engine`` (object with ``transcribe(path) -> dict``) or ``model``
(a name whisper.load_model understands). Loading a name may read a local
cache; this module does not call any download API of its own.
"""

# pylint: disable=import-outside-toplevel  # optional speech stacks are imported only when the adapter is used
# pylint: disable=attribute-defined-outside-init  # adapters set their backend state in initialize(), as in the LLM adapters

import tempfile
from typing import Any, Dict, Optional

from ai_platform.common.speech.base import SpeechAdapter
from ai_platform.common.speech.checks import require_audio
from ai_platform.common.speech.models import Transcript
from ai_platform.common.speech.speech_exception import SpeechConfigError, SpeechResponseError


class WhisperAdapter(SpeechAdapter):
    """Registry name: ``whisper``."""

    NAME = "whisper"
    CAPABILITIES = frozenset({"stt"})

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        SpeechAdapter.initialize(self, config)
        engine = self.config.get("engine")
        if engine is None:
            model = self.config.get("model")
            if not model:
                self.ready = False
                raise SpeechConfigError(
                    "WhisperAdapter requires config['model'] or config['engine']")
            try:
                import whisper
            except ImportError as exc:
                self.ready = False
                raise SpeechConfigError(
                    "WhisperAdapter requires: pip install openai-whisper") from exc
            engine = whisper.load_model(model)
        self.engine = engine

    def transcribe(self, audio, **kwargs) -> Transcript:
        self._require_ready()
        buffer = require_audio(audio)
        language = kwargs.get("language", self.config.get("language"))
        with tempfile.NamedTemporaryFile(prefix="whisper-", suffix=".wav", delete=False) as handle:
            path = handle.name
        buffer.write(path)
        options = {}
        if language:
            options["language"] = language
        result = self.engine.transcribe(path, **options)
        text = (result.get("text") or "").strip()
        if not text and not kwargs.get("allow_empty"):
            raise SpeechResponseError("whisper returned an empty transcript")
        return Transcript(
            text=text,
            engine=self.NAME,
            language=result.get("language", language),
            duration=buffer.duration,
            segments=list(result.get("segments") or []),
        )
