"""NVIDIA NeMo ASR.

``engine.transcribe([path]) -> [text]`` matches ``nemo.collections.asr``.
Pass that object, or ``model_name`` to call ``from_pretrained``. Restoring
a checkpoint is opt-in via ``model_name``.
"""

# pylint: disable=import-outside-toplevel  # optional speech stacks are imported only when the adapter is used
# pylint: disable=attribute-defined-outside-init  # adapters set their backend state in initialize(), as in the LLM adapters

import tempfile
from typing import Any, Dict, Optional

from ai_platform.common.speech.base import SpeechAdapter
from ai_platform.common.speech.checks import require_audio
from ai_platform.common.speech.models import Transcript
from ai_platform.common.speech.speech_exception import SpeechConfigError, SpeechResponseError


class NeMoAdapter(SpeechAdapter):
    """Registry name: ``nemo``."""

    NAME = "nemo"
    CAPABILITIES = frozenset({"stt"})

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        SpeechAdapter.initialize(self, config)
        engine = self.config.get("engine")
        if engine is None:
            model_name = self.config.get("model_name")
            if not model_name:
                self.ready = False
                raise SpeechConfigError("NeMoAdapter requires engine= or model_name=")
            try:
                import nemo.collections.asr as nemo_asr
            except ImportError as exc:
                self.ready = False
                raise SpeechConfigError(
                    "NeMoAdapter requires: pip install nemo_toolkit[asr]") from exc
            engine = nemo_asr.models.ASRModel.from_pretrained(model_name=model_name)
        self.engine = engine

    def transcribe(self, audio, **kwargs) -> Transcript:
        self._require_ready()
        buffer = require_audio(audio)
        with tempfile.NamedTemporaryFile(prefix="nemo-", suffix=".wav", delete=False) as handle:
            path = handle.name
        buffer.write(path)
        result = self.engine.transcribe([path])
        first = result[0] if result else ""
        text = first if isinstance(first, str) else getattr(first, "text", str(first))
        text = (text or "").strip()
        if not text and not kwargs.get("allow_empty"):
            raise SpeechResponseError("nemo returned an empty transcript")
        return Transcript(text=text, engine=self.NAME, duration=buffer.duration)
