"""Explicit registry of speech adapters.

Same shape as ``LLMRegistry`` / ``VideoToolRegistry``: no filesystem scan,
no registration on import. ``catalog.register_all`` is the explicit list.
"""

from typing import Dict, List, Type

from ai_platform.common.speech.base import SpeechAdapter


class SpeechRegistry:
    """Maps a stack name ("piper", "whisper", "cascade") to its adapter class."""

    def __init__(self) -> None:
        self._adapters: Dict[str, Type[SpeechAdapter]] = {}

    def register(self, name: str, adapter_class: Type[SpeechAdapter]) -> None:
        """Remember ``adapter_class`` under ``name``. Registering again replaces it."""
        if not name or not isinstance(name, str):
            raise ValueError("speech adapter name must be a non-empty string")
        self._adapters[name] = adapter_class

    def get(self, name: str) -> SpeechAdapter:
        """A new, not-yet-initialized instance."""
        if name not in self._adapters:
            known = ", ".join(self._adapters) or "(none)"
            raise ValueError(f"speech adapter '{name}' not registered; known: {known}")
        return self._adapters[name]()

    def get_class(self, name: str) -> Type[SpeechAdapter]:
        """The class, when the caller wants to inspect ``CAPABILITIES`` first."""
        if name not in self._adapters:
            raise ValueError(f"speech adapter '{name}' not registered")
        return self._adapters[name]

    def list(self) -> List[str]:
        """Registered names in insertion order."""
        return list(self._adapters)

    def list_by_capability(self, capability: str) -> List[str]:
        """Names whose class declares ``capability`` (``tts``, ``stt`` or ``sts``)."""
        return [
            name for name, cls in self._adapters.items()
            if capability in getattr(cls, "CAPABILITIES", ())
        ]


_registry = SpeechRegistry()


def get_registry() -> SpeechRegistry:
    """Process-wide registry. Tests that need isolation construct ``SpeechRegistry()``."""
    return _registry
