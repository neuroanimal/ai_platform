"""Microsoft Edge neural voices through the ``edge-tts`` package.

Online. Tests pass ``config['synthesize']``, a callable
``(text, voice, rate, pitch, path) -> None`` that writes the file.
The real package is used only when that callable is absent. The file is
usually MP3; bytes are returned in ``raw`` and PCM is left empty rather
than replaced with a fake waveform.
"""

# pylint: disable=import-outside-toplevel  # optional speech stacks are imported only when the adapter is used
# pylint: disable=attribute-defined-outside-init  # adapters set their backend state in initialize(), as in the LLM adapters

import asyncio
from typing import Any, Dict, Optional

from ai_platform.common.speech.audio_io import remove_quietly, temporary_path
from ai_platform.common.speech.base import SpeechAdapter
from ai_platform.common.speech.checks import require_text
from ai_platform.common.speech.models import AudioBuffer, SynthesisResult
from ai_platform.common.speech.speech_exception import SpeechConfigError, SpeechResponseError


def _save_with_edge_tts(text: str, voice: str, rate: str, pitch: str, path: str) -> None:
    """Synthesize with the edge-tts package (sends the text to Microsoft's service)."""
    import edge_tts  # pylint: disable=import-error
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    asyncio.run(communicate.save(path))


class EdgeTTSAdapter(SpeechAdapter):
    """Registry name: ``edge-tts``."""

    NAME = "edge-tts"
    CAPABILITIES = frozenset({"tts"})

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        SpeechAdapter.initialize(self, config)
        self._synthesize = self.config.get("synthesize")
        if self._synthesize is None:
            try:
                import edge_tts  # noqa: F401  # pylint: disable=import-error,unused-import
            except ImportError as exc:
                self.ready = False
                raise SpeechConfigError("EdgeTTSAdapter requires: pip install edge-tts") from exc
            if not self.config.get("allow_network"):
                self.ready = False
                raise SpeechConfigError(
                    "EdgeTTSAdapter calls Microsoft; set allow_network=True or pass synthesize="
                )
            self._synthesize = _save_with_edge_tts

    def synthesize(self, text: str, **kwargs) -> SynthesisResult:
        self._require_ready()
        sentence = require_text(text)
        voice = str(kwargs.get("voice", self.config.get("voice", "pl-PL-ZofiaNeural")))
        rate = str(kwargs.get("rate", self.config.get("rate", "+0%")))
        pitch = str(kwargs.get("pitch", self.config.get("pitch", "+0Hz")))
        target = kwargs.get("output_path")
        temporary = None  # removed after reading; the audio is returned in memory
        if not target:
            target = temporary_path("edge-", ".mp3")
            temporary = target
        try:
            self._synthesize(sentence, voice, rate, pitch, target)
            with open(target, "rb") as handle:
                raw = handle.read()
        except OSError as exc:
            raise SpeechResponseError(f"edge-tts did not write {target}") from exc
        finally:
            if temporary:
                remove_quietly(temporary)
        if not raw:
            raise SpeechResponseError("edge-tts wrote an empty file")
        # PCM is not invented from MP3. Callers that need samples decode it themselves.
        audio = AudioBuffer((), 24000)
        return SynthesisResult(
            audio=audio, engine=self.NAME, voice=voice, format="mp3", raw=raw,
            metadata={"output_path": None if temporary else target, "rate": rate,
                      "pitch": pitch, "pcm": False},
        )
