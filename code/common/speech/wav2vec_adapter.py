"""Wav2Vec2 through a Hugging Face ``pipeline('automatic-speech-recognition')``.

Pass the pipeline as ``engine``, or ``model`` to build one. ``model`` is
required so transformers is not imported, and no checkpoint is pulled,
until you name it.
"""

# pylint: disable=import-outside-toplevel  # optional speech stacks are imported only when the adapter is used
# pylint: disable=attribute-defined-outside-init  # adapters set their backend state in initialize(), as in the LLM adapters

import tempfile
from typing import Any, Dict, Optional

from ai_platform.common.speech.base import SpeechAdapter
from ai_platform.common.speech.checks import require_audio
from ai_platform.common.speech.models import Transcript
from ai_platform.common.speech.speech_exception import SpeechConfigError, SpeechResponseError


class Wav2VecAdapter(SpeechAdapter):
    """Registry name: ``wav2vec2``."""

    NAME = "wav2vec2"
    CAPABILITIES = frozenset({"stt"})

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        SpeechAdapter.initialize(self, config)
        engine = self.config.get("engine")
        if engine is None:
            model = self.config.get("model")
            if not model:
                self.ready = False
                raise SpeechConfigError(
                    "Wav2VecAdapter requires config['model'] or config['engine']")
            try:
                from transformers import pipeline
            except ImportError as exc:
                self.ready = False
                raise SpeechConfigError(
                    "Wav2VecAdapter requires: pip install transformers") from exc
            engine = pipeline("automatic-speech-recognition", model=model)
        self.engine = engine

    def transcribe(self, audio, **kwargs) -> Transcript:
        self._require_ready()
        buffer = require_audio(audio)
        with tempfile.NamedTemporaryFile(prefix="wav2vec-", suffix=".wav", delete=False) as handle:
            path = handle.name
        buffer.write(path)
        result = self.engine(path)
        if isinstance(result, dict):
            text = (result.get("text") or "").strip()
        else:
            text = str(result).strip()
        if not text and not kwargs.get("allow_empty"):
            raise SpeechResponseError("wav2vec2 returned an empty transcript")
        return Transcript(text=text, engine=self.NAME, duration=buffer.duration)
