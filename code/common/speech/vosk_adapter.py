"""Vosk offline recognizer.

Pass ``recognizer`` (``AcceptWaveform(pcm16_bytes)`` / ``Result()`` JSON),
or ``model_path`` so ``vosk.Model`` can be opened. Weights are not downloaded.
"""

# pylint: disable=import-outside-toplevel  # optional speech stacks are imported only when the adapter is used
# pylint: disable=attribute-defined-outside-init  # adapters set their backend state in initialize(), as in the LLM adapters

import json
from typing import Any, Dict, Optional

from ai_platform.common.speech.audio_io import pcm16_bytes
from ai_platform.common.speech.base import SpeechAdapter
from ai_platform.common.speech.checks import require_audio
from ai_platform.common.speech.models import Transcript
from ai_platform.common.speech.speech_exception import SpeechConfigError, SpeechResponseError


class VoskAdapter(SpeechAdapter):
    """Registry name: ``vosk``."""

    NAME = "vosk"
    CAPABILITIES = frozenset({"stt"})

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        SpeechAdapter.initialize(self, config)
        recognizer = self.config.get("recognizer")
        if recognizer is None:
            model_path = self.config.get("model_path")
            if not model_path:
                self.ready = False
                raise SpeechConfigError("VoskAdapter requires recognizer= or model_path=")
            try:
                import vosk
            except ImportError as exc:
                self.ready = False
                raise SpeechConfigError("VoskAdapter requires: pip install vosk") from exc
            model = vosk.Model(model_path)
            rate = int(self.config.get("sample_rate", 16000))
            recognizer = vosk.KaldiRecognizer(model, rate)
        self.recognizer = recognizer

    def transcribe(self, audio, **kwargs) -> Transcript:
        self._require_ready()
        buffer = require_audio(audio)
        pcm = pcm16_bytes(buffer.samples)
        self.recognizer.AcceptWaveform(pcm)
        raw = self.recognizer.Result()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            payload = json.loads(raw) if isinstance(raw, str) else dict(raw)
        except json.JSONDecodeError as exc:
            raise SpeechResponseError("vosk Result() was not JSON") from exc
        text = (payload.get("text") or "").strip()
        if not text and not kwargs.get("allow_empty"):
            raise SpeechResponseError("vosk returned an empty transcript")
        return Transcript(text=text, engine=self.NAME, duration=buffer.duration, segments=[payload])
