from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class NLPModel(BaseModel):
    """Common strict base for canonical NLP data models."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=False,
        str_strip_whitespace=True,
    )


class OffsetUnit(StrEnum):
    CODEPOINT = "codepoint"
    UTF8_BYTE = "utf8_byte"
    GRAPHEME_CLUSTER = "grapheme_cluster"


class ConfidenceScale(StrEnum):
    PROBABILITY = "probability"
    NORMALIZED_SCORE = "normalized_score"
    ORDINAL = "ordinal"
    UNSPECIFIED = "unspecified"


class ActorType(StrEnum):
    HUMAN = "human"
    MODEL = "model"
    RULE = "rule"
    SYSTEM = "system"
    EXTERNAL_TOOL = "external_tool"
    UNKNOWN = "unknown"


class TextSpan(NLPModel):
    """Half-open interval [start, end) in a specific text version."""

    start: int = Field(ge=0)
    end: int = Field(ge=0)
    offset_unit: OffsetUnit = OffsetUnit.CODEPOINT

    @model_validator(mode="after")
    def validate_order(self) -> "TextSpan":
        if self.end < self.start:
            raise ValueError("TextSpan.end cannot be smaller than start")
        return self

    @property
    def length(self) -> int:
        return self.end - self.start


class TextAnchor(NLPModel):
    """A reference to a span in one immutable text version."""

    text_version_id: str = Field(min_length=1)
    span: TextSpan
    quoted_text: str | None = None


class Confidence(NLPModel):
    value: float | None = Field(default=None, ge=0.0, le=1.0)
    scale: ConfidenceScale = ConfidenceScale.UNSPECIFIED
    label: str | None = None
    explanation: str | None = None


class Provenance(NLPModel):
    """Who or what produced an annotation, and under which conditions."""

    actor_type: ActorType = ActorType.UNKNOWN
    actor_id: str | None = None

    provider_id: str | None = None
    provider_version: str | None = None
    model_id: str | None = None
    model_revision: str | None = None

    method: str | None = None
    timestamp: datetime | None = None

    configuration: dict[str, Any] = Field(default_factory=dict)
    source_ids: list[str] = Field(default_factory=list)
    notes: str | None = None


class Evidence(NLPModel):
    """Evidence supporting an annotation or interpretation."""

    anchors: list[TextAnchor] = Field(default_factory=list)
    description: str | None = None
    provenance: Provenance | None = None
    confidence: Confidence | None = None

