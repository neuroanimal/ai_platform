
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NLP Graph Validator — standalone regression test.

Tests:
1. Valid graph structures.
2. Phrase graph cycle.
3. Constituency graph cycle.
4. Dependency graph cycle.
5. Clause embedding cycle.
"""

from ai_platform.common.nlp.model import (
    NLPAnalysis,
    Token,
    Phrase,
    DependencyRelation,
    ConstituencyNode,
    TextAnchor,
    TextSpan,
    OffsetUnit,
    Sentence,
    Clause,
)
from ai_platform.common.nlp.model.linguistic import (
    PhraseType,
    DependencyLayer,
)
from ai_platform.common.nlp.validation.graph_validator import (
    validate_graph_consistency,
)


TEXT = "Ala ma kota."


def anchor(start: int, end: int) -> TextAnchor:
    return TextAnchor(
        text_version_id="version-001",
        span=TextSpan(
            start=start,
            end=end,
            offset_unit=OffsetUnit.CODEPOINT,
        ),
    )


def build_analysis(
    phrase_cycle: bool = False,
    constituency_cycle: bool = False,
    dependency_cycle: bool = False,
    clause_cycle: bool = False,
) -> NLPAnalysis:

    sentences = [
        Sentence(
            sentence_id="sent-001",
            anchor=anchor(0, len(TEXT)),
            text=TEXT,
            sequence_number=1,
            token_ids=[
                "tok-001",
                "tok-002",
                "tok-003",
            ],
        )
    ]

    tokens = [
        Token(
            token_id="tok-001",
            text="Ala",
            anchor=anchor(0, 3),
            sentence_id="sent-001",
        ),
        Token(
            token_id="tok-002",
            text="ma",
            anchor=anchor(4, 6),
            sentence_id="sent-001",
        ),
        Token(
            token_id="tok-003",
            text="kota",
            anchor=anchor(7, 11),
            sentence_id="sent-001",
        ),
    ]

    phrase_type = next(iter(PhraseType))

    phrases = [
        Phrase(
            phrase_id="phrase-001",
            phrase_type=phrase_type,
            anchor=anchor(0, 12),
            token_ids=["tok-001", "tok-002", "tok-003"],
            head_token_id="tok-002",
            child_phrase_ids=["phrase-002"],
        ),
        Phrase(
            phrase_id="phrase-002",
            phrase_type=phrase_type,
            anchor=anchor(4, 11),
            token_ids=["tok-002", "tok-003"],
            head_token_id="tok-002",
            child_phrase_ids=(
                ["phrase-001"] if phrase_cycle else []
            ),
        ),
    ]

    constituency = [
        ConstituencyNode(
            node_id="node-001",
            label="S",
            anchor=anchor(0, 12),
            token_ids=["tok-001", "tok-002", "tok-003"],
            child_node_ids=["node-002"],
        ),
        ConstituencyNode(
            node_id="node-002",
            label="NP",
            anchor=anchor(0, 3),
            token_ids=["tok-001"],
            parent_node_id="node-001",
            child_node_ids=(
                ["node-001"] if constituency_cycle else []
            ),
        ),
    ]

    dependency_layer = next(iter(DependencyLayer))

    dependencies = [
        DependencyRelation(
            relation_id="dep-001",
            head_token_id="tok-001",
            dependent_token_id="tok-002",
            relation="nsubj",
            layer=dependency_layer,
        ),
        DependencyRelation(
            relation_id="dep-002",
            head_token_id="tok-002",
            dependent_token_id="tok-003",
            relation="obj",
            layer=dependency_layer,
        ),
    ]

    if dependency_cycle:
        dependencies.append(
            DependencyRelation(
                relation_id="dep-003",
                head_token_id="tok-003",
                dependent_token_id="tok-001",
                relation="cycle-test",
                layer=dependency_layer,
            )
        )

    clauses = []

    if clause_cycle:
        clauses = [
            Clause(
                clause_id="clause-001",
                anchor=anchor(0, 12),
                embedded_clause_ids=["clause-002"],
            ),
            Clause(
                clause_id="clause-002",
                anchor=anchor(4, 11),
                embedded_clause_ids=["clause-001"],
            ),
        ]

    return NLPAnalysis(
        analysis_id="analysis-001",
        document_id="document-001",
        text_version_id="version-001",
        sentences=sentences,
        tokens=tokens,
        phrases=phrases,
        clauses=clauses,
        dependencies=dependencies,
        constituency=constituency,
        predicate_arguments=[],
        hypotheses=[],
        completed_layers=[],
        unavailable_layers=[],
        metadata={},
    )


def run_test(
    name: str,
    analysis: NLPAnalysis,
    expected_valid: bool,
    expected_codes: set[str] | None = None,
    expected_warning_codes: set[str] | None = None,
) -> None:

    report = validate_graph_consistency(analysis)

    error_codes = {
        issue.code
        for issue in report.issues
        if issue.severity.value == "error"
    }

    warning_codes = {
        issue.code
        for issue in report.issues
        if issue.severity.value == "warning"
    }

    all_codes = error_codes | warning_codes

    print(f"\nTEST: {name}")
    print(f"VALID: {report.is_valid}")
    print(f"ERRORS: {sorted(error_codes)}")
    print(f"WARNINGS: {sorted(warning_codes)}")

    assert report.is_valid == expected_valid, (
        f"{name}: unexpected validation status"
    )

    if expected_codes:
        missing = expected_codes - all_codes

        assert not missing, (
            f"{name}: missing expected issue codes: {missing}"
        )

    if expected_warning_codes:
        missing = expected_warning_codes - warning_codes

        assert not missing, (
            f"{name}: missing expected warning codes: {missing}"
        )


def main() -> None:

    run_test(
        name="VALID GRAPH",
        analysis=build_analysis(),
        expected_valid=True,
    )

    run_test(
        name="PHRASE CYCLE",
        analysis=build_analysis(phrase_cycle=True),
        expected_valid=False,
        expected_codes={"phrase_graph_cycle"},
    )

    run_test(
        name="CONSTITUENCY CYCLE",
        analysis=build_analysis(constituency_cycle=True),
        expected_valid=False,
        expected_codes={"constituency_graph_cycle"},
    )

    run_test(
        name="DEPENDENCY CYCLE",
        analysis=build_analysis(dependency_cycle=True),
        expected_valid=True,
        expected_warning_codes={"dependency_graph_cycle"},
    )

    run_test(
        name="CLAUSE EMBEDDING CYCLE",
        analysis=build_analysis(clause_cycle=True),
        expected_valid=False,
        expected_codes={"clause_embedding_cycle"},
    )

    print("\nALL GRAPH VALIDATOR TESTS PASSED")


if __name__ == "__main__":
    main()


