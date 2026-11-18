from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from .base import NLPModel, Provenance, TextSpan


class TextRepresentation(StrEnum):
    DIPLOMATIC = "diplomatic"
    NORMALIZED = "normalized"
    EDITORIAL = "editorial"
    TRANSLITERATED = "transliterated"
    TRANSLATED = "translated"
    OCR_RAW = "ocr_raw"
    HTR_RAW = "htr_raw"
    OTHER = "other"


class SegmentType(StrEnum):
    DOCUMENT = "document"
    SECTION = "section"
    CHAPTER = "chapter"
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    FOOTNOTE = "footnote"
    CAPTION = "caption"
    TABLE_CELL = "table_cell"
    OTHER = "other"


class LanguageContext(NLPModel):
    """Language identification with optional temporal and regional scope."""

    language_code: str = Field(min_length=2)
    script: str | None = None
    dialect: str | None = None
    region: str | None = None
    linguistic_register: str | None = None

    valid_from: date | None = None
    valid_until: date | None = None

    historical_stage: str | None = None
    notes: str | None = None


class SourceDescriptor(NLPModel):
    """Description of the original source, not merely its extracted text."""

    source_id: str = Field(min_length=1)
    source_type: str
    title: str | None = None

    creator: str | None = None
    author: str | None = None
    speaker: str | None = None

    date_created: date | None = None
    date_range_start: date | None = None
    date_range_end: date | None = None

    repository: str | None = None
    shelfmark: str | None = None
    uri: str | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance | None = None


class TextSegment(NLPModel):
    segment_id: str = Field(min_length=1)
    segment_type: SegmentType

    text: str
    span: TextSpan | None = None

    parent_segment_id: str | None = None
    sequence_number: int | None = Field(default=None, ge=0)

    language: LanguageContext | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TextVersion(NLPModel):
    """An immutable textual representation of a source document."""

    text_version_id: str = Field(min_length=1)
    representation: TextRepresentation

    text: str
    language: LanguageContext | None = None

    segments: list[TextSegment] = Field(default_factory=list)

    derived_from_version_id: str | None = None
    transformation_description: str | None = None

    created_at: datetime | None = None
    provenance: Provenance | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NLPDocument(NLPModel):
    """Canonical document container."""

    document_id: str = Field(min_length=1)

    source: SourceDescriptor
    text_versions: list[TextVersion] = Field(default_factory=list)

    primary_text_version_id: str | None = None

    title: str | None = None
    document_language: LanguageContext | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)

