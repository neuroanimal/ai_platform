
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NLP GRAPH VALIDATOR — REGRESSION TESTS

Cel:
    Testy przypadków brzegowych walidatora grafów NLP.

Zakres:
    1. Powielone identyfikatory tokenów.
    2. Powielone identyfikatory relacji zależnościowych.
    3. Pętla własna w grafie zależnościowym.
    4. Niezgodna kolejność tokenów w zdaniu.
    5. Nakładające się zakresy tokenów.
    6. Rozłączne, ale poprawne grafy.
    7. Rozdzielenie grafów zależnościowych według scheme.
    8. Opcjonalny sequence_number (None).

Nie modyfikuje danych ani walidatora.
"""

from ai_platform.common.nlp.model import (
    NLPAnalysis,
    TextAnchor,
    TextSpan,
    OffsetUnit,
    Sentence,
    Token,
    Phrase,
    DependencyRelation,
    ConstituencyNode,
)

from ai_platform.common.nlp.model.linguistic import (
    PhraseType,
    DependencyLayer,
)

from ai_platform.common.nlp.validation.graph_validator import (
    validate_graph_consistency,
)


TEXT = "Ala ma kota."
VERSION_ID = "version-001"
PHRASE_TYPE = next(iter(PhraseType))
DEPENDENCY_LAYER = next(iter(DependencyLayer))


def anchor(start: int, end: int) -> TextAnchor:
    return TextAnchor(
        text_version_id=VERSION_ID,
        span=TextSpan(
            start=start,
            end=end,
            offset_unit=OffsetUnit.CODEPOINT,
        ),
    )


def make_token(
    token_id: str,
    text: str,
    start: int,
    end: int,
) -> Token:
    return Token(
        token_id=token_id,
        text=text,
        anchor=anchor(start, end),
    )


def make_sentence(
    sentence_id: str = "sent-001",
    start: int = 0,
    end: int = 12,
    sequence_number: int | None = 1,
    token_ids: list[str] | None = None,
) -> Sentence:
    return Sentence(
        sentence_id=sentence_id,
        anchor=anchor(start, end),
        text=TEXT[start:end],
        sequence_number=sequence_number,
        token_ids=token_ids or [],
    )


def make_dependency(
    relation_id: str,
    head_token_id: str,
    dependent_token_id: str,
    scheme: str | None = "test-scheme",
) -> DependencyRelation:
    return DependencyRelation(
        relation_id=relation_id,
        head_token_id=head_token_id,
        dependent_token_id=dependent_token_id,
        relation="dep",
        layer=DEPENDENCY_LAYER,
        scheme=scheme,
    )


def make_analysis(
    *,
    sentences: list[Sentence] | None = None,
    tokens: list[Token] | None = None,
    phrases: list[Phrase] | None = None,
    dependencies: list[DependencyRelation] | None = None,
    constituency: list[ConstituencyNode] | None = None,
) -> NLPAnalysis:
    return NLPAnalysis(
        analysis_id="analysis-regression",
        document_id="document-001",
        text_version_id=VERSION_ID,
        sentences=sentences if sentences is not None else [],
        tokens=tokens if tokens is not None else [],
        phrases=phrases if phrases is not None else [],
        clauses=[],
        dependencies=dependencies if dependencies is not None else [],
        constituency=constituency if constituency is not None else [],
        predicate_arguments=[],
        hypotheses=[],
        completed_layers=[],
        unavailable_layers=[],
        metadata={},
    )


def validate(analysis: NLPAnalysis):
    return validate_graph_consistency(analysis)


def issue_codes(report) -> set[str]:
    return {issue.code for issue in report.issues}


def print_result(name: str, report) -> None:
    errors = [
        issue.code
        for issue in report.issues
        if issue.severity.value == "error"
    ]
    warnings = [
        issue.code
        for issue in report.issues
        if issue.severity.value == "warning"
    ]

    print(f"\nTEST: {name}")
    print(f"VALID: {report.is_valid}")
    print(f"ERRORS: {errors}")
    print(f"WARNINGS: {warnings}")


def expect_code(report, code: str) -> None:
    codes = issue_codes(report)
    assert code in codes, (
        f"Expected issue code {code!r}, got: {sorted(codes)}"
    )


def expect_no_code(report, code: str) -> None:
    codes = issue_codes(report)
    assert code not in codes, (
        f"Unexpected issue code {code!r}, got: {sorted(codes)}"
    )


def test_duplicate_token_id() -> None:
    tokens = [
        make_token("tok-001", "Ala", 0, 3),
        make_token("tok-001", "ma", 4, 6),
    ]

    analysis = make_analysis(
        sentences=[
            make_sentence(token_ids=["tok-001"]),
        ],
        tokens=tokens,
    )

    report = validate(analysis)
    print_result("DUPLICATE TOKEN ID", report)

    assert not report.is_valid
    expect_code(report, "duplicate_token_id")


def test_duplicate_dependency_relation() -> None:
    tokens = [
        make_token("tok-001", "Ala", 0, 3),
        make_token("tok-002", "ma", 4, 6),
    ]

    dependencies = [
        make_dependency("dep-001", "tok-001", "tok-002"),
        make_dependency("dep-001", "tok-001", "tok-002"),
    ]

    analysis = make_analysis(
        tokens=tokens,
        dependencies=dependencies,
    )

    report = validate(analysis)
    print_result("DUPLICATE DEPENDENCY RELATION", report)

    assert not report.is_valid
    expect_code(report, "duplicate_dependency_relation")


def test_dependency_self_loop() -> None:
    tokens = [
        make_token("tok-001", "Ala", 0, 3),
    ]

    dependencies = [
        make_dependency("dep-001", "tok-001", "tok-001"),
    ]

    analysis = make_analysis(
        tokens=tokens,
        dependencies=dependencies,
    )

    report = validate(analysis)
    print_result("DEPENDENCY SELF-LOOP", report)

    assert not report.is_valid
    expect_code(report, "dependency_self_loop")


def test_sentence_token_order_mismatch() -> None:
    tokens = [
        make_token("tok-001", "Ala", 0, 3),
        make_token("tok-002", "ma", 4, 6),
    ]

    sentence = make_sentence(
        token_ids=["tok-002", "tok-001"],
    )

    analysis = make_analysis(
        sentences=[sentence],
        tokens=tokens,
    )

    report = validate(analysis)
    print_result("SENTENCE TOKEN ORDER MISMATCH", report)

    assert report.is_valid
    expect_code(report, "sentence_token_order_mismatch")


def test_overlapping_token_spans() -> None:
    tokens = [
        make_token("tok-001", "Ala m", 0, 5),
        make_token("tok-002", "ma", 4, 6),
    ]

    sentence = make_sentence(
        token_ids=["tok-001", "tok-002"],
    )

    analysis = make_analysis(
        sentences=[sentence],
        tokens=tokens,
    )

    report = validate(analysis)
    print_result("OVERLAPPING TOKEN SPANS", report)

    assert report.is_valid
    expect_code(report, "sentence_token_span_overlap")


def test_disconnected_valid_graphs() -> None:
    tokens = [
        make_token("tok-001", "Ala", 0, 3),
        make_token("tok-002", "ma", 4, 6),
        make_token("tok-003", "kota", 7, 11),
    ]

    phrases = [
        Phrase(
            phrase_id="phrase-001",
            phrase_type=PHRASE_TYPE,
            anchor=anchor(0, 3),
            token_ids=["tok-001"],
        ),
        Phrase(
            phrase_id="phrase-002",
            phrase_type=PHRASE_TYPE,
            anchor=anchor(4, 6),
            token_ids=["tok-002"],
        ),
    ]

    constituency = [
        ConstituencyNode(
            node_id="node-001",
            label="NP",
            anchor=anchor(0, 3),
            token_ids=["tok-001"],
        ),
        ConstituencyNode(
            node_id="node-002",
            label="NP",
            anchor=anchor(4, 6),
            token_ids=["tok-002"],
        ),
    ]

    dependencies = [
        make_dependency("dep-001", "tok-001", "tok-002"),
    ]

    analysis = make_analysis(
        tokens=tokens,
        phrases=phrases,
        constituency=constituency,
        dependencies=dependencies,
    )

    report = validate(analysis)
    print_result("DISCONNECTED VALID GRAPHS", report)

    assert report.is_valid
    assert not report.issues


def test_dependency_scheme_separation() -> None:
    """
    Dwa przeciwne kierunki relacji, ale należące do dwóch
    odrębnych schematów.

    Nie powinny zostać połączone w jeden cykl.
    """

    tokens = [
        make_token("tok-001", "Ala", 0, 3),
        make_token("tok-002", "ma", 4, 6),
    ]

    dependencies = [
        make_dependency(
            "dep-001",
            "tok-001",
            "tok-002",
            scheme="scheme-A",
        ),
        make_dependency(
            "dep-002",
            "tok-002",
            "tok-001",
            scheme="scheme-B",
        ),
    ]

    analysis = make_analysis(
        tokens=tokens,
        dependencies=dependencies,
    )

    report = validate(analysis)
    print_result("DEPENDENCY SCHEME SEPARATION", report)

    assert report.is_valid
    expect_no_code(report, "dependency_graph_cycle")


def test_optional_sentence_sequence_number() -> None:
    """
    sequence_number jest opcjonalny.
    Walidator powinien obsłużyć None razem z wartościami liczbowymi.
    """

    sentences = [
        make_sentence(
            sentence_id="sent-001",
            start=0,
            end=3,
            sequence_number=None,
        ),
        make_sentence(
            sentence_id="sent-002",
            start=4,
            end=12,
            sequence_number=1,
        ),
    ]

    analysis = make_analysis(
        sentences=sentences,
    )

    report = validate(analysis)
    print_result("OPTIONAL SENTENCE SEQUENCE NUMBER", report)

    assert report.is_valid


def main() -> None:
    tests = [
        test_duplicate_token_id,
        test_duplicate_dependency_relation,
        test_dependency_self_loop,
        test_sentence_token_order_mismatch,
        test_overlapping_token_spans,
        test_disconnected_valid_graphs,
        test_dependency_scheme_separation,
        test_optional_sentence_sequence_number,
    ]

    failures = []

    for test in tests:
        try:
            test()
        except Exception as exc:
            failures.append((test.__name__, exc))
            print(f"\nFAILED: {test.__name__}")
            print(f"{type(exc).__name__}: {exc}")

    print("\n" + "=" * 60)

    if failures:
        print(f"REGRESSION TESTS FAILED: {len(failures)}/{len(tests)}")

        for name, exc in failures:
            print(f"- {name}: {type(exc).__name__}: {exc}")

        raise SystemExit(1)

    print(f"ALL REGRESSION TESTS PASSED: {len(tests)}/{len(tests)}")


if __name__ == "__main__":
    main()


