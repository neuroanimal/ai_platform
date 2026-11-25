"""Speech pathway versus text pathway.

The same rewrite function is applied twice:

- text pathway: ``transform(text)`` on the original sentence;
- speech pathway: synthesize the sentence, recognize it, then ``transform``
  whatever the recognizer actually heard.

The gap between the two replies is the cost of going through audio. Which
TTS and which STT is up to the caller, so stacks can be swapped without
rewriting the comparison.
"""

# pylint: disable=import-outside-toplevel  # optional speech stacks are imported only when the adapter is used

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from ai_platform.common.speech.evaluation import wer
from ai_platform.common.speech.speech_exception import SpeechResponseError


Transform = Callable[[str], str]


@dataclass
class PathwayReport:  # pylint: disable=too-many-instance-attributes
    """Side-by-side result of one sentence."""

    text_in: str
    text_reply: str
    speech_transcript: str
    speech_reply: str
    input_wer: float
    reply_wer: float
    tts_engine: str
    stt_engine: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Serializable form."""
        return {
            "text_in": self.text_in,
            "text_reply": self.text_reply,
            "speech_transcript": self.speech_transcript,
            "speech_reply": self.speech_reply,
            "input_wer": self.input_wer,
            "reply_wer": self.reply_wer,
            "tts_engine": self.tts_engine,
            "stt_engine": self.stt_engine,
            "metadata": dict(self.metadata),
        }


def _call_transform(transform: Transform, text: str) -> str:
    try:
        reply = transform(text)
    except SpeechResponseError:
        raise
    except Exception as exc:
        raise SpeechResponseError(f"transform failed: {exc}") from exc
    if not isinstance(reply, str) or not reply.strip():
        raise SpeechResponseError("transform must return non-empty text")
    return reply


def compare_pathways(text: str, listener, speaker,
                     transform: Optional[Transform] = None) -> PathwayReport:
    """Run ``text`` through the text pathway and through TTS then STT.

    ``speaker`` must already be initialized and implement ``synthesize``.
    ``listener`` must already be initialized and implement ``transcribe``.
    ``transform`` defaults to the identity, which makes ``reply_wer`` equal
    ``input_wer`` and isolates recognition error from rewrite error.
    """
    from ai_platform.common.speech.checks import require_text

    sentence = require_text(text)
    rewrite = transform or (lambda heard: heard)
    text_reply = _call_transform(rewrite, sentence)
    spoken = speaker.synthesize(sentence)
    if not spoken.audio.samples:
        raise SpeechResponseError(
            f"{getattr(speaker, 'NAME', type(speaker).__name__)} returned no PCM; "
            "speech-vs-text needs a waveform the recognizer can hear"
        )
    heard = listener.transcribe(spoken.audio)
    speech_reply = _call_transform(rewrite, heard.text)
    return PathwayReport(
        text_in=sentence,
        text_reply=text_reply,
        speech_transcript=heard.text,
        speech_reply=speech_reply,
        input_wer=wer(sentence, heard.text),
        reply_wer=wer(text_reply, speech_reply),
        tts_engine=getattr(speaker, "NAME", ""),
        stt_engine=getattr(listener, "NAME", ""),
        metadata={
            "synthesis": spoken.to_dict(),
            "transcript": heard.to_dict(),
        },
    )
