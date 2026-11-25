"""Errors raised by speech adapters. Callers can catch ``SpeechError``."""


class SpeechError(Exception):
    """Base class for speech-domain failures."""


class SpeechConfigError(SpeechError):
    """Missing tool, model, key, or an adapter used before ``initialize``."""


class SpeechCapabilityError(SpeechError):
    """The adapter does not implement the requested direction (TTS, STT, STS)."""


class SpeechResponseError(SpeechError):
    """The input was refused or the backend returned nothing usable."""
