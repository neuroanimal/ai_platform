from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field

from .base import Confidence, Evidence, NLPModel, Provenance, TextAnchor


class DiscourseRelationType(StrEnum):
    ELABORATION = "elaboration"
    CONTRAST = "contrast"
    CAUSE = "cause"
    CONSEQUENCE = "consequence"
    CONDITION = "condition"
    TEMPORAL = "temporal"
    EXPLANATION = "explanation"
    BACKGROUND = "background"
    SEQUENCE = "sequence"
    OTHER = "other"
    UNKNOWN = "unknown"


class CoreferenceMention(NLPModel):
    mention_id: str = Field(min_length=1)
    anchor: TextAnchor

    referent_description: str | None = None
    grammatical_form: str | None = None

    confidence: Confidence | None = None
    provenance: Provenance | None = None


class CoreferenceChain(NLPModel):
    chain_id: str = Field(min_length=1)
    mention_ids: list[str] = Field(default_factory=list)

    canonical_reference: str | None = None
    entity_type: str | None = None

    confidence: Confidence | None = None
    provenance: Provenance | None = None


class DiscourseRelation(NLPModel):
    relation_id: str = Field(min_length=1)

    source_segment_id: str
    target_segment_id: str

    relation_type: DiscourseRelationType
    native_relation_label: str | None = None
    scheme: str | None = None

    evidence: list[Evidence] = Field(default_factory=list)
    confidence: Confidence | None = None
    provenance: Provenance | None = None


class SpeakerProfile(NLPModel):
    """A description of a speaker, distinct from document authorship."""

    speaker_id: str = Field(min_length=1)

    display_name: str | None = None
    role: str | None = None

    linguistic_profile: dict[str, Any] = Field(default_factory=dict)
    sociolinguistic_profile: dict[str, Any] = Field(default_factory=dict)

    valid_from: str | None = None
    valid_until: str | None = None

    evidence: list[Evidence] = Field(default_factory=list)
    provenance: Provenance | None = None


class SpeechAct(NLPModel):
    speech_act_id: str = Field(min_length=1)
    anchor: TextAnchor

    act_type: str
    illocutionary_force: str | None = None

    speaker_id: str | None = None
    addressee_ids: list[str] = Field(default_factory=list)

    propositional_content: str | None = None
    intended_effect: str | None = None

    explicitness: str | None = None
    discourse_function: str | None = None

    evidence: list[Evidence] = Field(default_factory=list)
    confidence: Confidence | None = None
    provenance: Provenance | None = None


class DiscourseAnnotation(NLPModel):
    """Discourse-level annotations associated with one analysis."""

    coreference_mentions: list[CoreferenceMention] = Field(default_factory=list)
    coreference_chains: list[CoreferenceChain] = Field(default_factory=list)

    relations: list[DiscourseRelation] = Field(default_factory=list)
    speakers: list[SpeakerProfile] = Field(default_factory=list)
    speech_acts: list[SpeechAct] = Field(default_factory=list)

    cohesion_features: list[dict[str, Any]] = Field(default_factory=list)
    discourse_properties: dict[str, Any] = Field(default_factory=dict)

