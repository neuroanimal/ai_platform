"""Festival's ``text2wave``. Classic concatenative TTS, command line.

The sentence is stdin. ``runner`` is injectable.
"""

# pylint: disable=import-outside-toplevel  # optional speech stacks are imported only when the adapter is used

from typing import Any, Dict, List, Optional

from ai_platform.common.speech.audio_io import remove_quietly, temporary_path
from ai_platform.common.speech.base import SpeechAdapter
from ai_platform.common.speech.checks import require_text
from ai_platform.common.speech.models import AudioBuffer, SynthesisResult
from ai_platform.common.speech.speech_exception import SpeechConfigError
from ai_platform.common.util.cli_runner import CLIToolMixin


def festival_command(executable: str, target: str) -> List[str]:
    """``text2wave -o <wav>``."""
    return [executable, "-o", target]


class FestivalAdapter(CLIToolMixin, SpeechAdapter):
    """Registry name: ``festival``."""

    NAME = "festival"
    CAPABILITIES = frozenset({"tts"})
    TOOLS = ["text2wave"]
    HINT = "install festival (the text2wave program)"
    ERROR = SpeechConfigError
    DEFAULT_TIMEOUT = 180.0

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
        target = kwargs.get("output_path")
        temporary = None  # removed after reading; the audio is returned in memory
        if not target:
            target = temporary_path("festival-", ".wav")
            temporary = target
        command = festival_command(self.executable, target)
        try:
            self._run_cli(command, stdin=sentence)
            audio = AudioBuffer.read(target)
        finally:
            if temporary:
                remove_quietly(temporary)
        return SynthesisResult(
            audio=audio, engine=self.NAME, voice="festival", format="wav",
            metadata={"output_path": None if temporary else target, "command": command},
        )
