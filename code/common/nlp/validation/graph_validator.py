
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Hashable, Iterable
from typing import TypeVar

from .structural_validator import (
    IssueSeverity,
    ValidationReport,
)
from ..model import NLPAnalysis


T = TypeVar("T")
NodeId = TypeVar("NodeId", bound=Hashable)


def _duplicates(values: Iterable[T]) -> set[T]:
    seen: set[T] = set()
    duplicates: set[T] = set()

    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)

    return duplicates


def _span_contains(parent: object, child: object) -> bool:
    """
    Checks whether parent's anchor span contains child's anchor span.

    Returns False when the anchors use different text versions
    or different offset units.
    """
    parent_anchor = getattr(parent, "anchor", None)
    child_anchor = getattr(child, "anchor", None)

    if parent_anchor is None or child_anchor is None:
        return False

    if parent_anchor.text_version_id != child_anchor.text_version_id:
        return False

    parent_span = parent_anchor.span
    child_span = child_anchor.span

    if parent_span.offset_unit != child_span.offset_unit:
        return False

    return (
        parent_span.start <= child_span.start
        and child_span.end <= parent_span.end
    )


def _find_cycles(
    adjacency: dict[NodeId, list[NodeId]],
) -> list[list[NodeId]]:
    """
    Detects directed cycles using depth-first search.

    Each detected cycle is returned once. The first node is repeated
    at the end to make the cycle explicit.
    """
    visited: set[NodeId] = set()
    active: list[NodeId] = []
    active_positions: dict[NodeId, int] = {}
    cycles: list[list[NodeId]] = []
    cycle_keys: set[frozenset[NodeId]] = set()

    def visit(node: NodeId) -> None:
        if node in visited:
            return

        visited.add(node)
        active_positions[node] = len(active)
        active.append(node)

        for child in adjacency.get(node, []):
            if child in active_positions:
                start = active_positions[child]
                cycle = active[start:] + [child]
                key = frozenset(cycle[:-1])

                if key not in cycle_keys:
                    cycle_keys.add(key)
                    cycles.append(cycle)

            elif child not in visited:
                visit(child)

        active.pop()
        del active_positions[node]

    all_nodes = set(adjacency)

    for children in adjacency.values():
        all_nodes.update(children)

    for node in all_nodes:
        if node not in visited:
            visit(node)

    return cycles


def _report_cycles(
    report: ValidationReport,
    code: str,
    label: str,
    cycles: list[list[Hashable]],
    severity: IssueSeverity = IssueSeverity.ERROR,
) -> None:
    for cycle in cycles:
        cycle_text = " -> ".join(str(node) for node in cycle)

        report.add(
            code,
            f"{label} contains a directed cycle: {cycle_text}.",
            severity=severity,
            object_id=str(cycle[0]),
        )


def _validate_unique_ids(
    report: ValidationReport,
    objects: list[object],
    id_attribute: str,
    label: str,
) -> None:
    ids = [getattr(obj, id_attribute) for obj in objects]

    for duplicate in _duplicates(ids):
        report.add(
            f"duplicate_{label}_id",
            f"Duplicate {label} ID: {duplicate}.",
            object_id=str(duplicate),
        )


def _validate_sentence_token_order(
    report: ValidationReport,
    analysis: NLPAnalysis,
) -> None:
    tokens = {token.token_id: token for token in analysis.tokens}

    ordered_sentences = sorted(
        analysis.sentences,
        # key=lambda sentence: sentence.sequence_number,
        key=lambda sentence: (
            sentence.sequence_number is None,
            sentence.sequence_number
            if sentence.sequence_number is not None
            else 0,
        ),
    )

    sequence_numbers = [
        sentence.sequence_number
        for sentence in analysis.sentences
    ]

    for duplicate in _duplicates(sequence_numbers):
        report.add(
            "duplicate_sentence_sequence",
            f"Multiple sentences use sequence number {duplicate}.",
            object_id=str(duplicate),
        )

    previous_sentence = None

    for sentence in ordered_sentences:
        if previous_sentence is not None:
            if (
                previous_sentence.anchor.text_version_id
                == sentence.anchor.text_version_id
                and previous_sentence.anchor.span.offset_unit
                == sentence.anchor.span.offset_unit
                and sentence.anchor.span.start
                < previous_sentence.anchor.span.start
            ):
                report.add(
                    "sentence_sequence_span_mismatch",
                    "Sentence sequence numbers do not match their "
                    "textual order.",
                    severity=IssueSeverity.WARNING,
                    object_id=sentence.sentence_id,
                )

        previous_sentence = sentence

        token_ids = sentence.token_ids

        for duplicate in _duplicates(token_ids):
            report.add(
                "duplicate_sentence_token",
                f"Sentence references token '{duplicate}' more than once.",
                object_id=sentence.sentence_id,
            )

        sentence_tokens = [
            tokens[token_id]
            for token_id in token_ids
            if token_id in tokens
        ]

        for left, right in zip(
            sentence_tokens,
            sentence_tokens[1:],
        ):
            left_span = left.anchor.span
            right_span = right.anchor.span

            if (
                left.anchor.text_version_id
                == right.anchor.text_version_id
                and left_span.offset_unit == right_span.offset_unit
                and right_span.start < left_span.start
            ):
                report.add(
                    "sentence_token_order_mismatch",
                    "Tokens are not ordered by their textual positions "
                    "inside the sentence.",
                    severity=IssueSeverity.WARNING,
                    object_id=sentence.sentence_id,
                )
                break

            if (
                left.anchor.text_version_id
                == right.anchor.text_version_id
                and left_span.offset_unit == right_span.offset_unit
                and right_span.start < left_span.end
            ):
                report.add(
                    "sentence_token_span_overlap",
                    "Consecutive tokens have overlapping text spans.",
                    severity=IssueSeverity.WARNING,
                    object_id=sentence.sentence_id,
                )
                break


def _validate_phrase_graph(
    report: ValidationReport,
    analysis: NLPAnalysis,
) -> None:
    phrases = {
        phrase.phrase_id: phrase
        for phrase in analysis.phrases
    }

    token_ids = {
        token.token_id
        for token in analysis.tokens
    }

    adjacency: dict[str, list[str]] = defaultdict(list)

    for phrase in analysis.phrases:
        if len(phrase.token_ids) != len(set(phrase.token_ids)):
            report.add(
                "duplicate_phrase_token",
                "Phrase contains duplicate token references.",
                object_id=phrase.phrase_id,
            )

        for token_id in phrase.token_ids:
            if token_id not in token_ids:
                report.add(
                    "unknown_phrase_token",
                    f"Phrase references unknown token '{token_id}'.",
                    object_id=phrase.phrase_id,
                )

        if (
            phrase.head_token_id is not None
            and phrase.head_token_id not in token_ids
        ):
            report.add(
                "unknown_phrase_head",
                f"Phrase head references unknown token "
                f"'{phrase.head_token_id}'.",
                object_id=phrase.phrase_id,
            )

        if (
            phrase.head_token_id is not None
            and phrase.head_token_id not in phrase.token_ids
        ):
            report.add(
                "phrase_head_not_in_phrase",
                "Phrase head token is not included in phrase token_ids.",
                object_id=phrase.phrase_id,
            )

        for child_id in phrase.child_phrase_ids:
            if child_id not in phrases:
                report.add(
                    "unknown_child_phrase",
                    f"Phrase references unknown child phrase '{child_id}'.",
                    object_id=phrase.phrase_id,
                )
                continue

            adjacency[phrase.phrase_id].append(child_id)

            child = phrases[child_id]

            if not _span_contains(phrase, child):
                report.add(
                    "phrase_child_span_outside_parent",
                    "Child phrase span is not contained in its parent "
                    "phrase span.",
                    severity=IssueSeverity.WARNING,
                    object_id=child_id,
                )

        for duplicate in _duplicates(phrase.child_phrase_ids):
            report.add(
                "duplicate_child_phrase",
                f"Phrase references child '{duplicate}' more than once.",
                object_id=phrase.phrase_id,
            )

    cycles = _find_cycles(adjacency)

    _report_cycles(
        report,
        "phrase_graph_cycle",
        "Phrase graph",
        cycles,
    )


def _validate_constituency_graph(
    report: ValidationReport,
    analysis: NLPAnalysis,
) -> None:
    nodes = {
        node.node_id: node
        for node in analysis.constituency
    }

    token_ids = {
        token.token_id
        for token in analysis.tokens
    }

    adjacency: dict[str, list[str]] = defaultdict(list)
    declared_parents: dict[str, set[str]] = defaultdict(set)

    for node in analysis.constituency:
        for token_id in node.token_ids:
            if token_id not in token_ids:
                report.add(
                    "unknown_constituency_token",
                    f"Constituency node references unknown token "
                    f"'{token_id}'.",
                    object_id=node.node_id,
                )

        for child_id in node.child_node_ids:
            if child_id not in nodes:
                report.add(
                    "unknown_constituency_child",
                    f"Constituency node references unknown child "
                    f"'{child_id}'.",
                    object_id=node.node_id,
                )
                continue

            adjacency[node.node_id].append(child_id)
            declared_parents[child_id].add(node.node_id)

            child = nodes[child_id]

            if child.parent_node_id != node.node_id:
                report.add(
                    "constituency_parent_child_mismatch",
                    f"Parent lists '{child_id}' as a child, but the "
                    f"child does not reference parent '{node.node_id}'.",
                    object_id=child_id,
                )

            if not _span_contains(node, child):
                report.add(
                    "constituency_child_span_outside_parent",
                    "Child node span is not contained in its parent node.",
                    severity=IssueSeverity.WARNING,
                    object_id=child_id,
                )

        for duplicate in _duplicates(node.child_node_ids):
            report.add(
                "duplicate_constituency_child",
                f"Constituency node references child '{duplicate}' "
                "more than once.",
                object_id=node.node_id,
            )

        if node.parent_node_id is not None:
            parent = nodes.get(node.parent_node_id)

            if parent is None:
                report.add(
                    "unknown_constituency_parent",
                    f"Constituency node references unknown parent "
                    f"'{node.parent_node_id}'.",
                    object_id=node.node_id,
                )
            elif node.node_id not in parent.child_node_ids:
                report.add(
                    "constituency_child_parent_mismatch",
                    f"Node references parent '{node.parent_node_id}', "
                    "but the parent does not list this node as a child.",
                    object_id=node.node_id,
                )

    for child_id, parents in declared_parents.items():
        if len(parents) > 1:
            report.add(
                "constituency_multiple_parents",
                f"Constituency node has multiple parents: "
                f"{', '.join(sorted(parents))}.",
                object_id=child_id,
            )

    cycles = _find_cycles(adjacency)

    _report_cycles(
        report,
        "constituency_graph_cycle",
        "Constituency graph",
        cycles,
    )


def _validate_dependency_graph(
    report: ValidationReport,
    analysis: NLPAnalysis,
) -> None:
    token_ids = {
        token.token_id
        for token in analysis.tokens
    }

    # Enhanced dependency representations can legitimately contain
    # multiple incoming edges. We therefore do not enforce one root
    # or one incoming edge per token.
    graphs: dict[tuple[object, object], dict[str, list[str]]] = (
        defaultdict(lambda: defaultdict(list))
    )

    seen_edges: set[tuple[object, ...]] = set()

    for dependency in analysis.dependencies:
        head_id = dependency.head_token_id
        dependent_id = dependency.dependent_token_id

        if dependent_id not in token_ids:
            report.add(
                "unknown_dependency_dependent",
                f"Dependency references unknown dependent token "
                f"'{dependent_id}'.",
                object_id=dependency.relation_id,
            )

        if head_id is not None and head_id not in token_ids:
            report.add(
                "unknown_dependency_head",
                f"Dependency references unknown head token "
                f"'{head_id}'.",
                object_id=dependency.relation_id,
            )

        if head_id is None:
            continue

        if head_id == dependent_id:
            report.add(
                "dependency_self_loop",
                "Dependency relation connects a token to itself.",
                object_id=dependency.relation_id,
            )
            continue

        edge_key = (
            head_id,
            dependent_id,
            dependency.relation,
            dependency.layer,
            dependency.scheme,
        )

        if edge_key in seen_edges:
            report.add(
                "duplicate_dependency_relation",
                "Duplicate dependency relation detected.",
                object_id=dependency.relation_id,
            )
        else:
            seen_edges.add(edge_key)

        graph_key = (
            dependency.layer,
            dependency.scheme,
        )

        graphs[graph_key][head_id].append(dependent_id)

    # Cycles are warnings rather than unconditional errors because
    # provider-native and enhanced dependency schemes can differ.
    for graph_key, adjacency in graphs.items():
        cycles = _find_cycles(adjacency)

        _report_cycles(
            report,
            "dependency_graph_cycle",
            f"Dependency graph {graph_key}",
            cycles,
            severity=IssueSeverity.WARNING,
        )


def _validate_clause_graph(
    report: ValidationReport,
    analysis: NLPAnalysis,
) -> None:
    clauses = {
        clause.clause_id: clause
        for clause in analysis.clauses
    }

    token_ids = {
        token.token_id
        for token in analysis.tokens
    }

    adjacency: dict[str, list[str]] = defaultdict(list)

    for clause in analysis.clauses:
        for token_id in (
            clause.predicate_token_ids
            + clause.subject_token_ids
        ):
            if token_id not in token_ids:
                report.add(
                    "unknown_clause_token",
                    f"Clause references unknown token '{token_id}'.",
                    object_id=clause.clause_id,
                )

        for embedded_id in clause.embedded_clause_ids:
            if embedded_id not in clauses:
                report.add(
                    "unknown_embedded_clause",
                    f"Clause references unknown embedded clause "
                    f"'{embedded_id}'.",
                    object_id=clause.clause_id,
                )
                continue

            adjacency[clause.clause_id].append(embedded_id)

        for duplicate in _duplicates(clause.embedded_clause_ids):
            report.add(
                "duplicate_embedded_clause",
                f"Clause references embedded clause '{duplicate}' "
                "more than once.",
                object_id=clause.clause_id,
            )

    cycles = _find_cycles(adjacency)

    _report_cycles(
        report,
        "clause_embedding_cycle",
        "Clause embedding graph",
        cycles,
    )


def validate_graph_consistency(
    analysis: NLPAnalysis,
) -> ValidationReport:
    """
    Validate graph and hierarchy consistency within an NLP analysis.

    This validator complements structural_validator.py.

    It does not require every NLP layer to be populated and does not
    enforce a universal dependency-tree or constituency convention.

    The caller should run structural validation first. This function
    focuses on graph relationships and cross-layer consistency.
    """
    report = ValidationReport()

    _validate_unique_ids(
        report,
        analysis.sentences,
        "sentence_id",
        "sentence",
    )
    _validate_unique_ids(
        report,
        analysis.tokens,
        "token_id",
        "token",
    )
    _validate_unique_ids(
        report,
        analysis.phrases,
        "phrase_id",
        "phrase",
    )
    _validate_unique_ids(
        report,
        analysis.clauses,
        "clause_id",
        "clause",
    )
    _validate_unique_ids(
        report,
        analysis.constituency,
        "node_id",
        "constituency_node",
    )
    _validate_unique_ids(
        report,
        analysis.dependencies,
        "relation_id",
        "dependency_relation",
    )

    _validate_sentence_token_order(report, analysis)
    _validate_phrase_graph(report, analysis)
    _validate_constituency_graph(report, analysis)
    _validate_dependency_graph(report, analysis)
    _validate_clause_graph(report, analysis)

    return report


