
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NLP Graph Validator — standalone smoke test.

Creates a minimal NLPAnalysis object and checks:
1. Valid graph structures.
2. Phrase graph cycle detection.
3. Constituency graph cycle detection.
4. Dependency graph cycle detection.
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
)
from ai_platform.common.nlp.validation.graph_validator import (
    validate_graph_consistency,
)


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
) -> NLPAnalysis:

    tokens = [
        Token(
            token_id="tok-001",
            surface="Ala",
            anchor=anchor(0, 3),
            sentence_id="sent-001",
        ),
        Token(
            token_id="tok-002",
            surface="ma",
            anchor=anchor(4, 6),
            sentence_id="sent-001",
        ),
        Token(
            token_id="tok-003",
            surface="kota",
            anchor=anchor(7, 11),
            sentence_id="sent-001",
        ),
    ]

    phrases = [
        Phrase(
            phrase_id="phrase-001",
            phrase_type="NP",
            token_ids=["tok-001"],
            head_token_id="tok-001",
            child_phrase_ids=["phrase-002"],
            anchor=anchor(0, 6),
        ),
        Phrase(
            phrase_id="phrase-002",
            phrase_type="VP-2",
            token_ids=["tok-002", "tok-003"],
            head_token_id="tok-002",
            child_phrase_ids=(
                ["phrase-001"] if phrase_cycle else []
            ),
            anchor=anchor(4, 11),
        ),
    ]

    constituency = [
        ConstituencyNode(
            node_id="node-001",
            label="S",
            token_ids=["tok-001", "tok-002", "tok-003"],
            child_node_ids=["node-002"],
            parent_node_id=None,
            anchor=anchor(0, 11),
        ),
        ConstituencyNode(
            node_id="node-002",
            label="NP",
            token_ids=["tok-001"],
            child_node_ids=(
                ["node-001"] if constituency_cycle else []
            ),
            parent_node_id="node-001",
            anchor=anchor(0, 3),
        ),
    ]

    dependencies = [
        DependencyRelation(
            relation_id="dep-001",
            head_token_id="tok-001",
            dependent_token_id="tok-002",
            relation="nsubj",
            layer="basic",
        ),
        DependencyRelation(
            relation_id="dep-002",
            head_token_id="tok-002",
            dependent_token_id="tok-003",
            relation="obj",
            layer="basic",
        ),
    ]

    if dependency_cycle:
        dependencies.append(
            DependencyRelation(
                relation_id="dep-003",
                head_token_id="tok-003",
                dependent_token_id="tok-001",
                relation="cycle-test",
                layer="basic",
            )
        )

    return NLPAnalysis(
        analysis_id="analysis-001",
        document_id="document-001",
        text_version_id="version-001",
        provider_id="test-provider",
        tokens=tokens,
        phrases=phrases,
        constituency=constituency,
        dependencies=dependencies,
    )


def run_test(
    name: str,
    analysis: NLPAnalysis,
    expected_valid: bool,
    expected_codes: set[str] | None = None,
) -> None:

    report = validate_graph_consistency(analysis)

    codes = {
        issue.code
        for issue in report.issues
    }

    print(f"\nTEST: {name}")
    print(f"VALID: {report.is_valid}")
    print(f"ISSUES: {sorted(codes)}")

    assert report.is_valid == expected_valid, (
        f"{name}: unexpected validation status"
    )

    if expected_codes:
        missing = expected_codes - codes

        assert not missing, (
            f"{name}: missing expected issue codes: {missing}"
        )


def main() -> None:

    run_test(
        "VALID GRAPH",
        build_analysis(),
        expected_valid=True,
    )

    run_test(
        "PHRASE CYCLE",
        build_analysis(phrase_cycle=True),
        expected_valid=False,
        expected_codes={"phrase_graph_cycle"},
    )

    run_test(
        "CONSTITUENCY CYCLE",
        build_analysis(constituency_cycle=True),
        expected_valid=False,
        expected_codes={"constituency_graph_cycle"},
    )

    run_test(
        "DEPENDENCY CYCLE",
        build_analysis(dependency_cycle=True),
        expected_valid=True,
        expected_codes={"dependency_graph_cycle"},
    )

    print("\nALL GRAPH VALIDATOR TESTS PASSED")


if __name__ == "__main__":
    main()


