"""Input checks shared by every adapter. Fail at the boundary, not deep inside."""

# pylint: disable=import-outside-toplevel  # optional speech stacks are imported only when the adapter is used

from ai_platform.common.speech.speech_exception import SpeechResponseError


def require_text(text) -> str:
    """A non-empty string. Surrounding whitespace is not speech."""
    if not isinstance(text, str):
        raise SpeechResponseError(f"text must be a string, got {type(text).__name__}")
    cleaned = text.strip()
    if not cleaned:
        raise SpeechResponseError("text is empty")
    return cleaned


def require_audio(audio):
    """Coerce ``audio`` to a non-empty mono ``AudioBuffer``."""
    # Local import: models import checks for nothing, but AudioBuffer lives there.
    from ai_platform.common.speech.models import AudioBuffer

    buffer = AudioBuffer.coerce(audio)
    if buffer.sample_rate <= 0:
        raise SpeechResponseError("sample_rate must be positive")
    if not buffer.samples:
        raise SpeechResponseError("audio is empty")
    return buffer
