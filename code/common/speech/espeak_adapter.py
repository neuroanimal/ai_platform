"""eSpeak NG / eSpeak, via the command line.

Text is passed on stdin, never through the shell. ``runner`` is injectable
and defaults to ``run_tool``.
"""

# pylint: disable=import-outside-toplevel  # optional speech stacks are imported only when the adapter is used

from typing import Any, Dict, List, Optional

from ai_platform.common.speech.audio_io import remove_quietly, temporary_path
from ai_platform.common.speech.base import SpeechAdapter
from ai_platform.common.speech.checks import require_text
from ai_platform.common.speech.models import AudioBuffer, SynthesisResult
from ai_platform.common.speech.speech_exception import SpeechConfigError
from ai_platform.common.util.cli_runner import CLIToolMixin


def espeak_command(executable: str, target: str, voice: str, wpm: int, pitch: int) -> List[str]:
    """Argument list. The utterance itself is stdin, so it cannot be parsed as a flag."""
    return [
        executable, "-v", str(voice), "-s", str(int(wpm)), "-p", str(int(pitch)),
        "-w", target,
    ]


class EspeakAdapter(CLIToolMixin, SpeechAdapter):
    """Registry name: ``espeak``."""

    NAME = "espeak"
    CAPABILITIES = frozenset({"tts"})
    TOOLS = ["espeak-ng", "espeak"]
    HINT = "install espeak-ng"
    ERROR = SpeechConfigError
    DEFAULT_TIMEOUT = 120.0

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        SpeechAdapter.initialize(self, config)
        try:
            self._configure_cli(self.config)
        except Exception:
            self.ready = False
            raise

    def synthesize(self, text: str, **kwargs) -> SynthesisResult:
        self._require_ready()
        sentence = require_text(text)
        voice = str(kwargs.get("voice", self.config.get("voice", "en")))
        wpm = int(kwargs.get("wpm", self.config.get("wpm", 160)))
        pitch = int(kwargs.get("pitch", self.config.get("pitch", 50)))
        if not 80 <= wpm <= 450:
            raise SpeechConfigError("espeak wpm must be between 80 and 450")
        if not 0 <= pitch <= 99:
            raise SpeechConfigError("espeak pitch must be between 0 and 99")
        target = kwargs.get("output_path")
        temporary = None
        if not target:
            target = temporary_path("espeak-", ".wav")
            temporary = target
        command = espeak_command(self.executable, target, voice, wpm, pitch)
        try:
            self._run_cli(command, stdin=sentence)
            audio = AudioBuffer.read(target)
        finally:
            if temporary:
                remove_quietly(temporary)
        return SynthesisResult(
            audio=audio, engine=self.NAME, voice=voice, format="wav",
            metadata={"wpm": wpm, "pitch": pitch, "output_path": None if temporary else target,
                      "command": command},
        )
