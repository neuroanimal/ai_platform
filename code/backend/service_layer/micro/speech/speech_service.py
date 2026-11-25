"""Service layer in front of the speech registry.

UI code talks to this module. It may depend on ``common`` (including an LLM
adapter passed in by the caller) and must not be imported by ``common``.
"""

import time
from typing import Any, Callable, Dict, List, Optional

from ai_platform.common.speech.catalog import register_all, stacks
from ai_platform.common.speech.compare import PathwayReport, compare_pathways
from ai_platform.common.speech.models import SpeechExchange, SynthesisResult, Transcript
from ai_platform.common.speech.speech_exception import SpeechConfigError, SpeechResponseError
from ai_platform.common.speech.speech_registry import SpeechRegistry


def llm_reply_transform(llm, system: Optional[str] = None) -> Callable[[str], str]:
    """Wrap any object that implements ``chat(messages) -> str``.

    The 17 LLM adapters in ``common.llm`` qualify. This function does not
    import them: the caller already chose one.
    """
    instruction = system or (
        "You are a voice assistant. Reply in the same language as the user, "
        "in one or two short spoken sentences, without markdown."
    )

    def transform(text: str) -> str:
        if not hasattr(llm, "chat"):
            raise SpeechConfigError("llm object has no chat()")
        reply = llm.chat([
            {"role": "system", "content": instruction},
            {"role": "user", "content": text},
        ])
        if not isinstance(reply, str):
            raise SpeechResponseError("llm.chat() must return a string")
        return reply

    return transform


class SpeechService:
    """Resolve a stack name and run one operation.

    A freshly constructed service has an empty registry until
    ``register_defaults``. Pass your own ``SpeechRegistry`` to stay isolated
    from the process-wide one.
    """

    def __init__(self, registry: Optional[SpeechRegistry] = None) -> None:
        self.registry = registry if registry is not None else SpeechRegistry()

    def register_defaults(self) -> "SpeechService":
        """Register every adapter of the catalog; returns self for chaining."""
        register_all(self.registry)
        return self

    def describe(self) -> List[Dict[str, Any]]:
        """Catalogue entries as plain dicts, for a CLI or a report."""
        return [
            {
                "name": spec.name,
                "kind": spec.kind,
                "family": spec.family,
                "offline": spec.offline,
                "needs": spec.needs,
                "summary": spec.summary,
            }
            for spec in stacks()
        ]

    def _owned(self, engine, config):
        if isinstance(engine, str):
            adapter = self.registry.get(engine)
            adapter.initialize(config or {})
            return adapter, True
        if config:
            engine.initialize(config)
        return engine, False

    def synthesize(self, engine, text: str, config: Optional[Dict[str, Any]] = None,
                   **kwargs) -> SynthesisResult:
        """Text to speech with ``engine`` (a registry name or an adapter)."""
        adapter, owned = self._owned(engine, config)
        try:
            started = time.perf_counter()
            result = adapter.synthesize(text, **kwargs)
            result.metadata["service_seconds"] = time.perf_counter() - started
            return result
        finally:
            if owned:
                adapter.shutdown()

    def transcribe(self, engine, audio, config: Optional[Dict[str, Any]] = None,
                   **kwargs) -> Transcript:
        """Speech to text with ``engine`` (a registry name or an adapter)."""
        adapter, owned = self._owned(engine, config)
        try:
            result = adapter.transcribe(audio, **kwargs)
            return result
        finally:
            if owned:
                adapter.shutdown()

    def converse(self, engine, audio, config: Optional[Dict[str, Any]] = None,
                 **kwargs) -> SpeechExchange:
        """Speech to speech with ``engine`` (a registry name or an adapter)."""
        adapter, owned = self._owned(engine, config)
        try:
            return adapter.converse(audio, **kwargs)
        finally:
            if owned:
                adapter.shutdown()

    def build_cascade(self, stt: str, tts: str, transform: Optional[Callable[[str], str]] = None,
                      stt_config: Optional[Dict[str, Any]] = None,
                      tts_config: Optional[Dict[str, Any]] = None):
        """Initialized cascade. The caller owns it and should ``shutdown`` it."""
        listener = self.registry.get(stt)
        listener.initialize(stt_config or {})
        speaker = self.registry.get(tts)
        speaker.initialize(tts_config or {})
        cascade = self.registry.get("cascade")
        cascade.initialize({"stt": listener, "tts": speaker, "transform": transform})
        return cascade

    def compare_text_and_speech(self, text: str, stt, tts,  # pylint: disable=too-many-arguments,too-many-positional-arguments
                                transform: Optional[Callable[[str], str]] = None,
                                stt_config: Optional[Dict[str, Any]] = None,
                                tts_config: Optional[Dict[str, Any]] = None) -> PathwayReport:
        """Text pathway versus TTS-then-STT pathway. Names or live adapters."""
        listener, own_stt = self._owned(stt, stt_config)
        speaker, own_tts = self._owned(tts, tts_config)
        try:
            return compare_pathways(text, listener, speaker, transform)
        finally:
            if own_stt:
                listener.shutdown()
            if own_tts:
                speaker.shutdown()
