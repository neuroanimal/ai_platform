"""faster-whisper (CTranslate2).

``engine.transcribe(path)`` must return ``(segments, info)`` like the real
library. ``model`` plus the package constructs one. No download is started
unless you pass a model name and the library itself fetches it.
"""

# pylint: disable=import-outside-toplevel  # optional speech stacks are imported only when the adapter is used
# pylint: disable=attribute-defined-outside-init  # adapters set their backend state in initialize(), as in the LLM adapters

import tempfile
from typing import Any, Dict, Optional

from ai_platform.common.speech.base import SpeechAdapter
from ai_platform.common.speech.checks import require_audio
from ai_platform.common.speech.models import Transcript
from ai_platform.common.speech.speech_exception import SpeechConfigError, SpeechResponseError


class FasterWhisperAdapter(SpeechAdapter):
    """Registry name: ``faster-whisper``."""

    NAME = "faster-whisper"
    CAPABILITIES = frozenset({"stt"})

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        SpeechAdapter.initialize(self, config)
        engine = self.config.get("engine")
        if engine is None:
            model = self.config.get("model")
            if not model:
                self.ready = False
                raise SpeechConfigError(
                    "FasterWhisperAdapter requires config['model'] or config['engine']"
                )
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                self.ready = False
                raise SpeechConfigError(
                    "FasterWhisperAdapter requires: pip install faster-whisper"
                ) from exc
            engine = WhisperModel(
                model,
                device=self.config.get("device", "cpu"),
                compute_type=self.config.get("compute_type", "int8"),
            )
        self.engine = engine

    def transcribe(self, audio, **kwargs) -> Transcript:
        self._require_ready()
        buffer = require_audio(audio)
        language = kwargs.get("language", self.config.get("language"))
        with tempfile.NamedTemporaryFile(prefix="fwhisper-", suffix=".wav", delete=False) as handle:
            path = handle.name
        buffer.write(path)
        segments, info = self.engine.transcribe(path, language=language)
        pieces = []
        stored = []
        for segment in segments:
            pieces.append(segment.text)
            stored.append({
                "start": getattr(segment, "start", None),
                "end": getattr(segment, "end", None),
                "text": segment.text,
            })
        text = " ".join(part.strip() for part in pieces).strip()
        if not text and not kwargs.get("allow_empty"):
            raise SpeechResponseError("faster-whisper returned an empty transcript")
        return Transcript(
            text=text,
            engine=self.NAME,
            language=getattr(info, "language", language),
            confidence=getattr(info, "language_probability", None),
            duration=buffer.duration,
            segments=stored,
        )
