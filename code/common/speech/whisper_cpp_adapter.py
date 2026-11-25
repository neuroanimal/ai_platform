"""whisper.cpp command line (``whisper-cli`` / ``main``).

Writes a temporary WAV, runs ``-otxt -of <base>`` and reads ``<base>.txt``.
``runner`` is injectable. The ggml model path is required.
"""

# pylint: disable=attribute-defined-outside-init  # adapters set their backend state in initialize(), as in the LLM adapters

import os
import shutil
import tempfile
from typing import Any, Dict, List, Optional

from ai_platform.common.speech.base import SpeechAdapter
from ai_platform.common.speech.checks import require_audio
from ai_platform.common.speech.models import Transcript
from ai_platform.common.speech.speech_exception import SpeechConfigError, SpeechResponseError
from ai_platform.common.util.cli_runner import CLIToolMixin


def whisper_cpp_command(executable: str, model: str, wav_path: str, output_base: str,
                        language: Optional[str] = None) -> List[str]:
    """Argument list for one file."""
    command = [executable, "-m", model, "-f", wav_path, "-otxt", "-of", output_base, "-np"]
    if language:
        command += ["-l", language]
    return command


class WhisperCppAdapter(CLIToolMixin, SpeechAdapter):
    """Registry name: ``whisper-cpp``."""

    NAME = "whisper-cpp"
    CAPABILITIES = frozenset({"stt"})
    # The old whisper.cpp binary was called "main"; that name is too generic to
    # look up on PATH (it could run an unrelated program), so pass it via config.
    TOOLS = ["whisper-cli", "whisper-cpp"]
    HINT = "install whisper.cpp and pass config['model']"
    ERROR = SpeechConfigError
    DEFAULT_TIMEOUT = 600.0

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        SpeechAdapter.initialize(self, config)
        model = self.config.get("model")
        if not model:
            self.ready = False
            raise SpeechConfigError("WhisperCppAdapter requires config['model'] (ggml path)")
        self.model = str(model)
        try:
            self._configure_cli(self.config)
        except Exception:
            self.ready = False
            raise

    def transcribe(self, audio, **kwargs) -> Transcript:
        self._require_ready()
        buffer = require_audio(audio)
        language = kwargs.get("language", self.config.get("language"))
        directory = tempfile.mkdtemp(prefix="whispercpp-")
        try:
            wav_path = os.path.join(directory, "in.wav")
            output_base = os.path.join(directory, "out")
            buffer.write(wav_path)
            command = whisper_cpp_command(self.executable, self.model, wav_path, output_base,
                                          language)
            self._run_cli(command)
            txt_path = output_base + ".txt"
            if not os.path.exists(txt_path):
                raise SpeechResponseError("whisper.cpp did not write a transcript")
            with open(txt_path, "r", encoding="utf-8") as handle:
                text = handle.read().strip()
        finally:
            shutil.rmtree(directory, ignore_errors=True)
        if not text and not kwargs.get("allow_empty"):
            raise SpeechResponseError("whisper.cpp returned an empty transcript")
        return Transcript(
            text=text, engine=self.NAME, language=language, duration=buffer.duration,
            segments=[{"command": command}],
        )
