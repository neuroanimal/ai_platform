from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field

from .base import (
    Confidence,
    Evidence,
    NLPModel,
    Provenance,
    TextAnchor,
)


class PartOfSpeech(StrEnum):
    NOUN = "noun"
    PROPER_NOUN = "proper_noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"
    PRONOUN = "pronoun"
    DETERMINER = "determiner"
    NUMERAL = "numeral"
    ADPOSITION = "adposition"
    CONJUNCTION = "conjunction"
    PARTICLE = "particle"
    INTERJECTION = "interjection"
    AUXILIARY = "auxiliary"
    OTHER = "other"
    UNKNOWN = "unknown"


class PhraseType(StrEnum):
    NP = "NP"
    VP_0 = "VP-0"
    VP_1 = "VP-1"
    VP_2 = "VP-2"
    VP_3 = "VP-3"
    AP = "AP"
    ADVP = "AdvP"
    PP = "PP"
    CLAUSE = "Clause"
    OTHER = "Other"


class DependencyLayer(StrEnum):
    UNIVERSAL_DEPENDENCIES = "universal_dependencies"
    LANGUAGE_SPECIFIC = "language_specific"
    PROVIDER_NATIVE = "provider_native"
    PROJECT_DEFINED = "project_defined"


class SyntacticFunction(StrEnum):
    SUBJECT = "subject"
    DIRECT_OBJECT = "direct_object"
    INDIRECT_OBJECT = "indirect_object"
    PREDICATE = "predicate"
    ATTRIBUTE = "attribute"
    ADJUNCT = "adjunct"
    COMPLEMENT = "complement"
    MODIFIER = "modifier"
    COORDINATE = "coordinate"
    OTHER = "other"
    UNKNOWN = "unknown"


class SemanticRole(StrEnum):
    AGENT = "agent"
    PATIENT = "patient"
    THEME = "theme"
    EXPERIENCER = "experiencer"
    STIMULUS = "stimulus"
    RECIPIENT = "recipient"
    BENEFICIARY = "beneficiary"
    INSTRUMENT = "instrument"
    LOCATION = "location"
    SOURCE = "source"
    GOAL = "goal"
    CAUSE = "cause"
    TIME = "time"
    MANNER = "manner"
    OTHER = "other"
    UNKNOWN = "unknown"


class MorphologicalFeature(NLPModel):
    category: str
    value: str
    language_specific: bool = False
    scheme: str | None = None


class Token(NLPModel):
    token_id: str = Field(min_length=1)
    anchor: TextAnchor

    text: str
    normalized_form: str | None = None
    lemma: str | None = None

    upos: PartOfSpeech | None = None
    xpos: str | None = None
    pos_scheme: str | None = None

    morphology: list[MorphologicalFeature] = Field(default_factory=list)

    is_punctuation: bool = False
    is_stopword: bool | None = None

    sentence_id: str | None = None
    multiword_token_id: str | None = None

    confidence: Confidence | None = None
    provenance: Provenance | None = None
    provider_native: dict[str, Any] = Field(default_factory=dict)


class Phrase(NLPModel):
    phrase_id: str = Field(min_length=1)
    phrase_type: PhraseType

    anchor: TextAnchor
    head_token_id: str | None = None

    child_phrase_ids: list[str] = Field(default_factory=list)
    token_ids: list[str] = Field(default_factory=list)

    grammatical_features: dict[str, Any] = Field(default_factory=dict)
    syntactic_function: SyntacticFunction | None = None

    confidence: Confidence | None = None
    provenance: Provenance | None = None
    provider_native: dict[str, Any] = Field(default_factory=dict)


class DependencyRelation(NLPModel):
    relation_id: str = Field(min_length=1)

    head_token_id: str
    dependent_token_id: str

    relation: str
    layer: DependencyLayer
    syntactic_function: SyntacticFunction | None = None

    subtype: str | None = None
    scheme: str | None = None

    confidence: Confidence | None = None
    provenance: Provenance | None = None


class ConstituencyNode(NLPModel):
    node_id: str = Field(min_length=1)
    label: str

    anchor: TextAnchor
    parent_node_id: str | None = None

    child_node_ids: list[str] = Field(default_factory=list)
    token_ids: list[str] = Field(default_factory=list)

    scheme: str | None = None
    provenance: Provenance | None = None


class Clause(NLPModel):
    clause_id: str = Field(min_length=1)
    anchor: TextAnchor

    clause_type: str | None = None
    is_main_clause: bool | None = None
    is_finite: bool | None = None

    predicate_token_ids: list[str] = Field(default_factory=list)
    subject_token_ids: list[str] = Field(default_factory=list)

    embedded_clause_ids: list[str] = Field(default_factory=list)
    syntactic_function: SyntacticFunction | None = None

    confidence: Confidence | None = None
    provenance: Provenance | None = None
    provider_native: dict[str, Any] = Field(default_factory=dict)


class PredicateArgument(NLPModel):
    argument_id: str = Field(min_length=1)

    predicate_token_id: str
    argument_token_ids: list[str] = Field(default_factory=list)
    argument_phrase_id: str | None = None

    semantic_role: SemanticRole
    role_label_native: str | None = None
    role_scheme: str | None = None

    evidence: list[Evidence] = Field(default_factory=list)
    confidence: Confidence | None = None
    provenance: Provenance | None = None

