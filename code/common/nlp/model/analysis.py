from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from .base import Confidence, NLPModel, Provenance
from .discourse import DiscourseAnnotation
from .linguistic import (
    Clause,
    ConstituencyNode,
    DependencyRelation,
    Phrase,
    PredicateArgument,
    Token,
)
from .segmentation import Sentence


class AnalysisStatus(StrEnum):
    DRAFT = "draft"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    REVIEWED = "reviewed"
    ADJUDICATED = "adjudicated"


class HypothesisStatus(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ALTERNATIVE = "alternative"
    UNRESOLVED = "unresolved"


class AnalysisLayer(StrEnum):
    SEGMENTATION = "segmentation"
    MORPHOLOGY = "morphology"
    LEXICON = "lexicon"
    PHRASE_STRUCTURE = "phrase_structure"
    DEPENDENCY_SYNTAX = "dependency_syntax"
    CONSTITUENCY_SYNTAX = "constituency_syntax"
    CLAUSE_STRUCTURE = "clause_structure"
    SEMANTICS = "semantics"
    DISCOURSE = "discourse"
    PRAGMATICS = "pragmatics"
    DIALECTOLOGY = "dialectology"
    DIACHRONY = "diachrony"
    OTHER = "other"


class AnnotationHypothesis(NLPModel):
    hypothesis_id: str = Field(min_length=1)

    layer: AnalysisLayer
    target_id: str | None = None

    interpretation: dict[str, Any]
    status: HypothesisStatus = HypothesisStatus.PROPOSED

    confidence: Confidence | None = None
    rationale: str | None = None

    alternative_to_hypothesis_id: str | None = None
    provenance: Provenance | None = None


class ProviderMetadata(NLPModel):
    provider_id: str
    provider_version: str | None = None

    model_id: str | None = None
    model_revision: str | None = None

    language_code: str | None = None
    configuration: dict[str, Any] = Field(default_factory=dict)

    runtime_seconds: float | None = Field(default=None, ge=0.0)
    hardware: dict[str, Any] = Field(default_factory=dict)

    raw_output_reference: str | None = None
    raw_output: dict[str, Any] | None = None


class NLPAnalysis(NLPModel):
    analysis_id: str = Field(min_length=1)

    document_id: str
    text_version_id: str

    status: AnalysisStatus = AnalysisStatus.DRAFT
    created_at: datetime | None = None

    provider: ProviderMetadata | None = None

    sentences: list[Sentence] = Field(default_factory=list)
    tokens: list[Token] = Field(default_factory=list)
    phrases: list[Phrase] = Field(default_factory=list)
    clauses: list[Clause] = Field(default_factory=list)

    dependencies: list[DependencyRelation] = Field(default_factory=list)
    constituency: list[ConstituencyNode] = Field(default_factory=list)

    predicate_arguments: list[PredicateArgument] = Field(default_factory=list)
    discourse: DiscourseAnnotation | None = None

    hypotheses: list[AnnotationHypothesis] = Field(default_factory=list)

    completed_layers: list[AnalysisLayer] = Field(default_factory=list)
    unavailable_layers: list[AnalysisLayer] = Field(default_factory=list)

    provenance: Provenance | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

