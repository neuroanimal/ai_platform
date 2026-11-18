from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from .base import Confidence, NLPModel, Provenance, TextAnchor


class SentenceType(StrEnum):
    DECLARATIVE = "declarative"
    INTERROGATIVE = "interrogative"
    IMPERATIVE = "imperative"
    EXCLAMATIVE = "exclamative"
    FRAGMENT = "fragment"
    OTHER = "other"
    UNKNOWN = "unknown"


class Sentence(NLPModel):
    """Sentence-level unit in a particular text version."""

    sentence_id: str = Field(min_length=1)
    anchor: TextAnchor

    text: str
    sequence_number: int | None = Field(default=None, ge=0)

    sentence_type: SentenceType | None = None
    language_code: str | None = None

    token_ids: list[str] = Field(default_factory=list)
    clause_ids: list[str] = Field(default_factory=list)

    is_complete: bool | None = None
    confidence: Confidence | None = None
    provenance: Provenance | None = None

