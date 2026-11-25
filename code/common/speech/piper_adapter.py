"""Piper TTS (https://github.com/rhasspy/piper). Neural, local, ONNX.

The ``--model`` path is required. Weights are never downloaded from here.
"""

# pylint: disable=import-outside-toplevel  # optional speech stacks are imported only when the adapter is used
# pylint: disable=attribute-defined-outside-init  # adapters set their backend state in initialize(), as in the LLM adapters

from typing import Any, Dict, List, Optional

from ai_platform.common.speech.audio_io import remove_quietly, temporary_path
from ai_platform.common.speech.base import SpeechAdapter
from ai_platform.common.speech.checks import require_text
from ai_platform.common.speech.models import AudioBuffer, SynthesisResult
from ai_platform.common.speech.speech_exception import SpeechConfigError
from ai_platform.common.util.cli_runner import CLIToolMixin


def piper_command(executable: str, model: str, target: str,
                  speaker: Optional[str] = None) -> List[str]:
    """Argument list. The sentence is stdin."""
    command = [executable, "--model", model, "--output_file", target]
    if speaker is not None:
        command += ["--speaker", str(speaker)]
    return command


class PiperAdapter(CLIToolMixin, SpeechAdapter):
    """Registry name: ``piper``."""

    NAME = "piper"
    CAPABILITIES = frozenset({"tts"})
    TOOLS = ["piper"]
    HINT = "install piper and pass config['model'] (an .onnx voice)"
    ERROR = SpeechConfigError
    DEFAULT_TIMEOUT = 180.0

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        SpeechAdapter.initialize(self, config)
        model = self.config.get("model")
        if not model:
            self.ready = False
            raise SpeechConfigError("PiperAdapter requires config['model'] (.onnx voice)")
        self.model = str(model)
        self.speaker = self.config.get("speaker")
        try:
            self._configure_cli(self.config)
        except Exception:
            self.ready = False
            raise

    def synthesize(self, text: str, **kwargs) -> SynthesisResult:
        self._require_ready()
        sentence = require_text(text)
        target = kwargs.get("output_path")
        temporary = None  # removed after reading; the audio is returned in memory
        if not target:
            target = temporary_path("piper-", ".wav")
            temporary = target
        speaker = kwargs.get("speaker", self.speaker)
        command = piper_command(self.executable, self.model, target, speaker)
        try:
            self._run_cli(command, stdin=sentence)
            audio = AudioBuffer.read(target)
        finally:
            if temporary:
                remove_quietly(temporary)
        return SynthesisResult(
            audio=audio, engine=self.NAME,
            voice=str(speaker if speaker is not None else self.model),
            format="wav", metadata={"model": self.model,
                                    "output_path": None if temporary else target,
                                       "command": command},
        )
