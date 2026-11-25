"""OpenAI audio speech API, and any server that copies it (LocalAI, ...).

``POST {base_url}/audio/speech`` with JSON. ``opener`` replaces urllib in tests.
``response_format=wav`` is decoded to PCM. Other formats stay in ``raw``.
"""

# pylint: disable=attribute-defined-outside-init  # adapters set their backend state in initialize(), as in the LLM adapters

import os
from typing import Any, Dict, Optional

from ai_platform.common.speech.base import SpeechAdapter
from ai_platform.common.speech.checks import require_text
from ai_platform.common.speech.http_api import bearer, post_json, urllib_opener
from ai_platform.common.speech.models import AudioBuffer, SynthesisResult
from ai_platform.common.speech.speech_exception import SpeechConfigError, SpeechResponseError


class OpenAITTSAdapter(SpeechAdapter):
    """Registry name: ``openai-tts``."""

    NAME = "openai-tts"
    CAPABILITIES = frozenset({"tts"})

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        SpeechAdapter.initialize(self, config)
        self.opener = self.config.get("opener", urllib_opener)
        self.api_key = self.config.get("api_key") or os.environ.get("OPENAI_API_KEY")
        self.base_url = str(self.config.get("base_url", "https://api.openai.com/v1")).rstrip("/")
        self.model = str(self.config.get("model", "tts-1"))
        self.timeout = float(self.config.get("timeout", 60))
        self.response_format = str(self.config.get("response_format", "wav"))
        if not self.api_key:
            self.ready = False
            raise SpeechConfigError("OpenAITTSAdapter requires api_key or OPENAI_API_KEY")

    def synthesize(self, text: str, **kwargs) -> SynthesisResult:
        self._require_ready()
        sentence = require_text(text)
        voice = str(kwargs.get("voice", self.config.get("voice", "alloy")))
        response_format = str(kwargs.get("response_format", self.response_format))
        payload = {
            "model": kwargs.get("model", self.model),
            "input": sentence,
            "voice": voice,
            "response_format": response_format,
        }
        if "speed" in kwargs or "speed" in self.config:
            payload["speed"] = float(kwargs.get("speed", self.config.get("speed")))
        raw = post_json(
            self.base_url + "/audio/speech", payload, bearer(self.api_key),
            self.timeout, self.opener,
        )
        if not raw:
            raise SpeechResponseError("openai-tts returned an empty body")
        if response_format == "wav" or raw[:4] == b"RIFF":
            audio = AudioBuffer.from_wav_bytes(raw)
            fmt = "wav"
        else:
            audio = AudioBuffer((), 24000)
            fmt = response_format
        return SynthesisResult(
            audio=audio, engine=self.NAME, voice=voice, format=fmt, raw=raw,
            metadata={"model": payload["model"], "pcm": bool(audio.samples)},
        )
