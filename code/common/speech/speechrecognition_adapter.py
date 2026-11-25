"""The ``SpeechRecognition`` library, several backends behind one call.

``recognize(wav_path) -> text`` short-circuits the library (tests, or your
own backend). Network backends (``google``, ``google_cloud``, ``wit``,
``bing``) are refused unless ``allow_network`` is set. The default backend
name is PocketSphinx (``sphinx``), which is offline when installed.
"""

# pylint: disable=import-outside-toplevel  # optional speech stacks are imported only when the adapter is used
# pylint: disable=attribute-defined-outside-init  # adapters set their backend state in initialize(), as in the LLM adapters

import tempfile
from typing import Any, Dict, Optional

from ai_platform.common.speech.base import SpeechAdapter
from ai_platform.common.speech.checks import require_audio
from ai_platform.common.speech.models import Transcript
from ai_platform.common.speech.speech_exception import SpeechConfigError, SpeechResponseError

_NETWORK = {"google", "google_cloud", "wit", "bing", "houndify", "ibm"}


class SpeechRecognitionAdapter(SpeechAdapter):
    """Registry name: ``speechrecognition``."""

    NAME = "speechrecognition"
    CAPABILITIES = frozenset({"stt"})

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        SpeechAdapter.initialize(self, config)
        self.backend = str(self.config.get("backend", "sphinx"))
        self._recognize = self.config.get("recognize")
        if self._recognize is not None:
            return
        if self.backend in _NETWORK and not self.config.get("allow_network"):
            self.ready = False
            raise SpeechConfigError(
                f"SpeechRecognition backend {self.backend!r} needs the network; "
                "set allow_network=True or pass recognize="
            )
        try:
            import speech_recognition as sr
        except ImportError as exc:
            self.ready = False
            raise SpeechConfigError(
                "SpeechRecognitionAdapter requires: pip install SpeechRecognition"
            ) from exc
        self._sr = sr
        self._recognizer = sr.Recognizer()

    def transcribe(self, audio, **kwargs) -> Transcript:
        self._require_ready()
        buffer = require_audio(audio)
        with tempfile.NamedTemporaryFile(prefix="sr-", suffix=".wav", delete=False) as handle:
            path = handle.name
        buffer.write(path)
        if self._recognize is not None:
            text = self._recognize(path)
        else:
            with self._sr.AudioFile(path) as source:
                recorded = self._recognizer.record(source)
            method = getattr(self._recognizer, "recognize_" + self.backend, None)
            if method is None:
                raise SpeechConfigError(f"SpeechRecognition has no recognize_{self.backend}")
            try:
                text = method(recorded)
            except self._sr.UnknownValueError as exc:
                raise SpeechResponseError(f"{self.backend} could not understand the audio") from exc
        text = (text or "").strip()
        if not text and not kwargs.get("allow_empty"):
            raise SpeechResponseError("speechrecognition returned an empty transcript")
        return Transcript(
            text=text, engine=self.NAME, language=kwargs.get("language"),
            duration=buffer.duration, segments=[{"backend": self.backend}],
        )
