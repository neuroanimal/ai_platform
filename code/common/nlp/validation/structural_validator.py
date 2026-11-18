from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from ..model import NLPAnalysis, NLPDocument
from ..model.base import OffsetUnit, TextAnchor, TextSpan
from ..model.linguistic import (
    Clause,
    ConstituencyNode,
    DependencyRelation,
    Phrase,
    PredicateArgument,
    Token,
)


class IssueSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class ValidationIssue:
    """One structural validation finding."""

    def __init__(
        self,
        code: str,
        message: str,
        severity: IssueSeverity = IssueSeverity.ERROR,
        object_id: str | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.severity = severity
        self.object_id = object_id

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "object_id": self.object_id,
        }


class ValidationReport:
    """Collection of structural validation findings."""

    def __init__(self) -> None:
        self.issues: list[ValidationIssue] = []

    @property
    def is_valid(self) -> bool:
        return not any(
            issue.severity == IssueSeverity.ERROR
            for issue in self.issues
        )

    @property
    def errors(self) -> list[ValidationIssue]:
        return [
            issue for issue in self.issues
            if issue.severity == IssueSeverity.ERROR
        ]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [
            issue for issue in self.issues
            if issue.severity == IssueSeverity.WARNING
        ]

    def add(
        self,
        code: str,
        message: str,
        severity: IssueSeverity = IssueSeverity.ERROR,
        object_id: str | None = None,
    ) -> None:
        self.issues.append(
            ValidationIssue(code, message, severity, object_id)
        )

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "issues": [issue.to_dict() for issue in self.issues],
        }


def _check_unique_ids(
    report: ValidationReport,
    objects: list,
    id_attribute: str,
    collection_name: str,
) -> set[str]:
    seen: set[str] = set()

    for obj in objects:
        object_id = getattr(obj, id_attribute)

        if object_id in seen:
            report.add(
                "duplicate_id",
                f"Duplicate {id_attribute} '{object_id}' "
                f"in {collection_name}.",
                object_id=object_id,
            )

        seen.add(object_id)

    return seen


def _check_span(
    report: ValidationReport,
    span: TextSpan,
    text: str,
    object_id: str | None,
) -> None:
    if span.offset_unit == OffsetUnit.CODEPOINT:
        text_length = len(text)
    elif span.offset_unit == OffsetUnit.UTF8_BYTE:
        text_length = len(text.encode("utf-8"))
    else:
        # Grapheme-cluster counting requires Unicode segmentation.
        # It is deliberately not approximated using Python len().
        return

    if span.end > text_length:
        report.add(
            "span_out_of_bounds",
            f"Span end {span.end} exceeds text length {text_length}.",
            object_id=object_id,
        )


def _check_anchor(
    report: ValidationReport,
    anchor: TextAnchor,
    text_versions: dict,
    object_id: str | None,
) -> None:
    version = text_versions.get(anchor.text_version_id)

    if version is None:
        report.add(
            "unknown_text_version",
            f"Unknown text version '{anchor.text_version_id}'.",
            object_id=object_id,
        )
        return

    _check_span(report, anchor.span, version.text, object_id)

    if (
        anchor.quoted_text is not None
        and anchor.span.offset_unit == OffsetUnit.CODEPOINT
    ):
        actual = version.text[anchor.span.start:anchor.span.end]

        if actual != anchor.quoted_text:
            report.add(
                "anchor_quote_mismatch",
                "Quoted text does not match the referenced text span.",
                IssueSeverity.WARNING,
                object_id,
            )


def validate_document_analysis(
    document: NLPDocument,
    analysis: NLPAnalysis,
) -> ValidationReport:
    """Validate cross-object consistency of a document and its analysis."""

    report = ValidationReport()

    # ---------------------------------------------------------
    # Document and text versions
    # ---------------------------------------------------------

    text_version_ids = _check_unique_ids(
        report,
        document.text_versions,
        "text_version_id",
        "document.text_versions",
    )

    text_versions = {
        version.text_version_id: version
        for version in document.text_versions
    }

    if document.primary_text_version_id is not None:
        if document.primary_text_version_id not in text_version_ids:
            report.add(
                "unknown_primary_text_version",
                "Primary text version does not exist in the document.",
                object_id=document.document_id,
            )

    if analysis.document_id != document.document_id:
        report.add(
            "document_id_mismatch",
            "Analysis references a different document.",
            object_id=analysis.analysis_id,
        )

    if analysis.text_version_id not in text_version_ids:
        report.add(
            "analysis_text_version_missing",
            "Analysis references a text version absent from the document.",
            object_id=analysis.analysis_id,
        )

    selected_version = text_versions.get(analysis.text_version_id)

    # ---------------------------------------------------------
    # Document segments
    # ---------------------------------------------------------

    all_segments = [
        segment
        for version in document.text_versions
        for segment in version.segments
    ]

    segment_ids = _check_unique_ids(
        report,
        all_segments,
        "segment_id",
        "document.segments",
    )

    for version in document.text_versions:
        local_segment_ids = {
            segment.segment_id for segment in version.segments
        }

        for segment in version.segments:
            if segment.span is not None:
                _check_span(
                    report,
                    segment.span,
                    version.text,
                    segment.segment_id,
                )

            if (
                segment.parent_segment_id is not None
                and segment.parent_segment_id not in local_segment_ids
            ):
                report.add(
                    "unknown_segment_parent",
                    "Parent segment does not exist in the same text version.",
                    object_id=segment.segment_id,
                )

    # ---------------------------------------------------------
    # Analysis collection identifiers
    # ---------------------------------------------------------

    sentence_ids = _check_unique_ids(
        report, analysis.sentences, "sentence_id", "analysis.sentences"
    )
    token_ids = _check_unique_ids(
        report, analysis.tokens, "token_id", "analysis.tokens"
    )
    phrase_ids = _check_unique_ids(
        report, analysis.phrases, "phrase_id", "analysis.phrases"
    )
    clause_ids = _check_unique_ids(
        report, analysis.clauses, "clause_id", "analysis.clauses"
    )
    constituency_ids = _check_unique_ids(
        report,
        analysis.constituency,
        "node_id",
        "analysis.constituency",
    )
    dependency_ids = _check_unique_ids(
        report,
        analysis.dependencies,
        "relation_id",
        "analysis.dependencies",
    )
    argument_ids = _check_unique_ids(
        report,
        analysis.predicate_arguments,
        "argument_id",
        "analysis.predicate_arguments",
    )

    # ---------------------------------------------------------
    # Text anchors
    # ---------------------------------------------------------

    anchored_objects = (
        list(analysis.sentences)
        + list(analysis.tokens)
        + list(analysis.phrases)
        + list(analysis.clauses)
        + list(analysis.constituency)
    )

    for obj in anchored_objects:
        _check_anchor(
            report,
            obj.anchor,
            text_versions,
            getattr(obj, "sentence_id", None)
            or getattr(obj, "token_id", None)
            or getattr(obj, "phrase_id", None)
            or getattr(obj, "clause_id", None)
            or getattr(obj, "node_id", None),
        )

        if obj.anchor.text_version_id != analysis.text_version_id:
            report.add(
                "analysis_anchor_version_mismatch",
                "Annotation anchor belongs to a different text version "
                "than the analysis.",
                object_id=(
                    getattr(obj, "sentence_id", None)
                    or getattr(obj, "token_id", None)
                    or getattr(obj, "phrase_id", None)
                    or getattr(obj, "clause_id", None)
                    or getattr(obj, "node_id", None)
                ),
            )

    # ---------------------------------------------------------
    # Sentence and token relations
    # ---------------------------------------------------------

    for sentence in analysis.sentences:
        for token_id in sentence.token_ids:
            if token_id not in token_ids:
                report.add(
                    "unknown_sentence_token",
                    f"Sentence references unknown token '{token_id}'.",
                    object_id=sentence.sentence_id,
                )

        for clause_id in sentence.clause_ids:
            if clause_id not in clause_ids:
                report.add(
                    "unknown_sentence_clause",
                    f"Sentence references unknown clause '{clause_id}'.",
                    object_id=sentence.sentence_id,
                )

    for token in analysis.tokens:
        if token.sentence_id is not None:
            if token.sentence_id not in sentence_ids:
                report.add(
                    "unknown_token_sentence",
                    f"Token references unknown sentence "
                    f"'{token.sentence_id}'.",
                    object_id=token.token_id,
                )

        if selected_version is not None:
            _check_token_surface(report, token, selected_version.text)

    # ---------------------------------------------------------
    # Phrase relations
    # ---------------------------------------------------------

    for phrase in analysis.phrases:
        if (
            phrase.head_token_id is not None
            and phrase.head_token_id not in token_ids
        ):
            report.add(
                "unknown_phrase_head",
                f"Phrase head token '{phrase.head_token_id}' does not exist.",
                object_id=phrase.phrase_id,
            )

        for token_id in phrase.token_ids:
            if token_id not in token_ids:
                report.add(
                    "unknown_phrase_token",
                    f"Phrase references unknown token '{token_id}'.",
                    object_id=phrase.phrase_id,
                )

        for child_id in phrase.child_phrase_ids:
            if child_id not in phrase_ids:
                report.add(
                    "unknown_child_phrase",
                    f"Child phrase '{child_id}' does not exist.",
                    object_id=phrase.phrase_id,
                )

    # ---------------------------------------------------------
    # Dependency relations
    # ---------------------------------------------------------

    for relation in analysis.dependencies:
        if relation.head_token_id not in token_ids:
            report.add(
                "unknown_dependency_head",
                f"Dependency head '{relation.head_token_id}' does not exist.",
                object_id=relation.relation_id,
            )

        if relation.dependent_token_id not in token_ids:
            report.add(
                "unknown_dependency_dependent",
                "Dependency dependent token does not exist.",
                object_id=relation.relation_id,
            )

        if relation.head_token_id == relation.dependent_token_id:
            report.add(
                "dependency_self_reference",
                "Dependency relation cannot point from a token to itself.",
                object_id=relation.relation_id,
            )

    # ---------------------------------------------------------
    # Constituency relations
    # ---------------------------------------------------------

    for node in analysis.constituency:
        if (
            node.parent_node_id is not None
            and node.parent_node_id not in constituency_ids
        ):
            report.add(
                "unknown_constituency_parent",
                "Constituency parent node does not exist.",
                object_id=node.node_id,
            )

        for child_id in node.child_node_ids:
            if child_id not in constituency_ids:
                report.add(
                    "unknown_constituency_child",
                    f"Constituency child '{child_id}' does not exist.",
                    object_id=node.node_id,
                )

        for token_id in node.token_ids:
            if token_id not in token_ids:
                report.add(
                    "unknown_constituency_token",
                    f"Constituency node references unknown token '{token_id}'.",
                    object_id=node.node_id,
                )

    # ---------------------------------------------------------
    # Clause relations
    # ---------------------------------------------------------

    for clause in analysis.clauses:
        for token_id in (
            clause.predicate_token_ids + clause.subject_token_ids
        ):
            if token_id not in token_ids:
                report.add(
                    "unknown_clause_token",
                    f"Clause references unknown token '{token_id}'.",
                    object_id=clause.clause_id,
                )

        for child_id in clause.embedded_clause_ids:
            if child_id not in clause_ids:
                report.add(
                    "unknown_embedded_clause",
                    f"Embedded clause '{child_id}' does not exist.",
                    object_id=clause.clause_id,
                )

    # ---------------------------------------------------------
    # Predicate-argument relations
    # ---------------------------------------------------------

    for argument in analysis.predicate_arguments:
        if argument.predicate_token_id not in token_ids:
            report.add(
                "unknown_argument_predicate",
                "Predicate-argument structure references an unknown predicate.",
                object_id=argument.argument_id,
            )

        if (
            argument.argument_phrase_id is not None
            and argument.argument_phrase_id not in phrase_ids
        ):
            report.add(
                "unknown_argument_phrase",
                "Predicate-argument structure references an unknown phrase.",
                object_id=argument.argument_id,
            )

        for token_id in argument.argument_token_ids:
            if token_id not in token_ids:
                report.add(
                    "unknown_argument_token",
                    f"Argument references unknown token '{token_id}'.",
                    object_id=argument.argument_id,
                )

    # ---------------------------------------------------------
    # Discourse relations
    # ---------------------------------------------------------

    if analysis.discourse is not None:
        discourse = analysis.discourse

        mention_ids = _check_unique_ids(
            report,
            discourse.coreference_mentions,
            "mention_id",
            "discourse.coreference_mentions",
        )
        _check_unique_ids(
            report,
            discourse.coreference_chains,
            "chain_id",
            "discourse.coreference_chains",
        )
        _check_unique_ids(
            report,
            discourse.relations,
            "relation_id",
            "discourse.relations",
        )
        speaker_ids = _check_unique_ids(
            report,
            discourse.speakers,
            "speaker_id",
            "discourse.speakers",
        )
        _check_unique_ids(
            report,
            discourse.speech_acts,
            "speech_act_id",
            "discourse.speech_acts",
        )

        for mention in discourse.coreference_mentions:
            _check_anchor(
                report, mention.anchor, text_versions, mention.mention_id
            )

        for chain in discourse.coreference_chains:
            for mention_id in chain.mention_ids:
                if mention_id not in mention_ids:
                    report.add(
                        "unknown_coreference_mention",
                        f"Coreference chain references unknown mention "
                        f"'{mention_id}'.",
                        object_id=chain.chain_id,
                    )

        for relation in discourse.relations:
            if relation.source_segment_id not in segment_ids:
                report.add(
                    "unknown_discourse_source",
                    "Discourse relation source segment does not exist.",
                    object_id=relation.relation_id,
                )

            if relation.target_segment_id not in segment_ids:
                report.add(
                    "unknown_discourse_target",
                    "Discourse relation target segment does not exist.",
                    object_id=relation.relation_id,
                )

        for speech_act in discourse.speech_acts:
            _check_anchor(
                report,
                speech_act.anchor,
                text_versions,
                speech_act.speech_act_id,
            )

            if (
                speech_act.speaker_id is not None
                and speech_act.speaker_id not in speaker_ids
            ):
                report.add(
                    "unknown_speech_act_speaker",
                    "Speech act references an unknown speaker.",
                    object_id=speech_act.speech_act_id,
                )

            for addressee_id in speech_act.addressee_ids:
                if addressee_id not in speaker_ids:
                    report.add(
                        "unknown_speech_act_addressee",
                        f"Unknown addressee '{addressee_id}'.",
                        object_id=speech_act.speech_act_id,
                    )

    return report


def _check_token_surface(
    report: ValidationReport,
    token: Token,
    text: str,
) -> None:
    span = token.anchor.span

    if span.offset_unit == OffsetUnit.CODEPOINT:
        actual = text[span.start:span.end]
    elif span.offset_unit == OffsetUnit.UTF8_BYTE:
        encoded = text.encode("utf-8")
        try:
            actual = encoded[span.start:span.end].decode("utf-8")
        except UnicodeDecodeError:
            report.add(
                "token_offset_splits_utf8",
                "Token byte offsets split a UTF-8 character.",
                object_id=token.token_id,
            )
            return
    else:
        # Grapheme offsets need a dedicated Unicode segmentation provider.
        return

    if actual != token.text:
        report.add(
            "token_surface_mismatch",
            f"Token surface '{token.text}' differs from source span '{actual}'.",
            IssueSeverity.WARNING,
            token.token_id,
        )

