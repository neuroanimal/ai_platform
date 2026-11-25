"""OpenAI transcriptions API (``/audio/transcriptions``), also LocalAI-compatible.

Audio is posted as WAV multipart. ``opener`` replaces urllib in tests.
"""

# pylint: disable=attribute-defined-outside-init  # adapters set their backend state in initialize(), as in the LLM adapters

import json
import os
from typing import Any, Dict, Optional

from ai_platform.common.speech.base import SpeechAdapter
from ai_platform.common.speech.checks import require_audio
from ai_platform.common.speech.http_api import bearer, post_multipart, urllib_opener
from ai_platform.common.speech.models import Transcript
from ai_platform.common.speech.speech_exception import SpeechConfigError, SpeechResponseError


class OpenAISTTAdapter(SpeechAdapter):
    """Registry name: ``openai-stt``."""

    NAME = "openai-stt"
    CAPABILITIES = frozenset({"stt"})

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        SpeechAdapter.initialize(self, config)
        self.opener = self.config.get("opener", urllib_opener)
        self.api_key = self.config.get("api_key") or os.environ.get("OPENAI_API_KEY")
        self.base_url = str(self.config.get("base_url", "https://api.openai.com/v1")).rstrip("/")
        self.model = str(self.config.get("model", "whisper-1"))
        self.timeout = float(self.config.get("timeout", 60))
        if not self.api_key:
            self.ready = False
            raise SpeechConfigError("OpenAISTTAdapter requires api_key or OPENAI_API_KEY")

    def transcribe(self, audio, **kwargs) -> Transcript:
        self._require_ready()
        buffer = require_audio(audio)
        fields = {"model": str(kwargs.get("model", self.model))}
        language = kwargs.get("language", self.config.get("language"))
        if language:
            fields["language"] = language
        raw = post_multipart(
            self.base_url + "/audio/transcriptions",
            fields,
            [("file", "audio.wav", buffer.to_wav_bytes(), "audio/wav")],
            bearer(self.api_key),
            self.timeout,
            self.opener,
        )
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SpeechResponseError("openai-stt returned non-JSON") from exc
        text = (payload.get("text") or "").strip()
        if not text and not kwargs.get("allow_empty"):
            raise SpeechResponseError("openai-stt returned an empty transcript")
        return Transcript(
            text=text, engine=self.NAME, language=payload.get("language", language),
            duration=buffer.duration, segments=list(payload.get("segments") or []),
        )
