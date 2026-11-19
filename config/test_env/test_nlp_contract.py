
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NLP MODEL CONTRACT TESTS

Zakres:
    1. Kompletność publicznych eksportów modelu.
    2. Generowanie JSON Schema dla NLPDocument i NLPAnalysis.
    3. Kontrola wymaganych pól w schematach.
    4. Serializacja i deserializacja modeli.
    5. Round-trip Python -> JSON -> Python.
    6. Odrzucanie niepoprawnych danych JSON.

Nie modyfikuje modeli ani wcześniejszych testów.
"""

import json

from pydantic import ValidationError

import ai_platform.common.nlp.model as nlp_model

from ai_platform.common.nlp.model import (
    AnalysisLayer,
    AnalysisStatus,
    LanguageContext,
    NLPAnalysis,
    NLPDocument,
    OffsetUnit,
    ProviderMetadata,
    SegmentType,
    Sentence,
    SourceDescriptor,
    TextAnchor,
    TextRepresentation,
    TextSegment,
    TextSpan,
    TextVersion,
    Token,
)


TEXT = "Ala ma kota."
VERSION_ID = "version-001"
DOCUMENT_ID = "document-001"


def build_document() -> NLPDocument:
    language = LanguageContext(
        language_code="pl",
        script="Latn",
        historical_stage="modern",
    )

    source = SourceDescriptor(
        source_id="source-001",
        source_type="text",
        title="Dokument testowy",
        author="Autor testowy",
        metadata={
            "collection": "nlp-contract-tests",
            "test": True,
        },
    )

    segment = TextSegment(
        segment_id="segment-001",
        segment_type=SegmentType.PARAGRAPH,
        text=TEXT,
        span=TextSpan(
            start=0,
            end=len(TEXT),
            offset_unit=OffsetUnit.CODEPOINT,
        ),
        language=language,
        sequence_number=0,
    )

    version = TextVersion(
        text_version_id=VERSION_ID,
        representation=TextRepresentation.DIPLOMATIC,
        text=TEXT,
        language=language,
        segments=[segment],
        metadata={
            "origin": "contract-test",
        },
    )

    return NLPDocument(
        document_id=DOCUMENT_ID,
        source=source,
        text_versions=[version],
        primary_text_version_id=VERSION_ID,
        title="Testowy dokument NLP",
        document_language=language,
        metadata={
            "test_case": "document-round-trip",
        },
    )


def build_analysis() -> NLPAnalysis:
    sentence_anchor = TextAnchor(
        text_version_id=VERSION_ID,
        span=TextSpan(
            start=0,
            end=len(TEXT),
            offset_unit=OffsetUnit.CODEPOINT,
        ),
        quoted_text=TEXT,
    )

    sentence = Sentence(
        sentence_id="sentence-001",
        anchor=sentence_anchor,
        text=TEXT,
        sequence_number=0,
        token_ids=[
            "token-001",
            "token-002",
            "token-003",
        ],
    )

    tokens = [
        Token(
            token_id="token-001",
            text="Ala",
            anchor=TextAnchor(
                text_version_id=VERSION_ID,
                span=TextSpan(
                    start=0,
                    end=3,
                    offset_unit=OffsetUnit.CODEPOINT,
                ),
                quoted_text="Ala",
            ),
            sentence_id="sentence-001",
        ),
        Token(
            token_id="token-002",
            text="ma",
            anchor=TextAnchor(
                text_version_id=VERSION_ID,
                span=TextSpan(
                    start=4,
                    end=6,
                    offset_unit=OffsetUnit.CODEPOINT,
                ),
                quoted_text="ma",
            ),
            sentence_id="sentence-001",
        ),
        Token(
            token_id="token-003",
            text="kota",
            anchor=TextAnchor(
                text_version_id=VERSION_ID,
                span=TextSpan(
                    start=7,
                    end=11,
                    offset_unit=OffsetUnit.CODEPOINT,
                ),
                quoted_text="kota",
            ),
            sentence_id="sentence-001",
        ),
    ]

    provider = ProviderMetadata(
        provider_id="test-provider",
        provider_version="1.0.0",
        model_id="test-model",
        language_code="pl",
        configuration={
            "mode": "contract-test",
        },
        runtime_seconds=0.25,
        hardware={
            "device": "cpu",
        },
    )

    return NLPAnalysis(
        analysis_id="analysis-001",
        document_id=DOCUMENT_ID,
        text_version_id=VERSION_ID,
        status=AnalysisStatus.COMPLETED,
        provider=provider,
        sentences=[sentence],
        tokens=tokens,
        completed_layers=[
            AnalysisLayer.SEGMENTATION,
        ],
        metadata={
            "test_case": "analysis-round-trip",
        },
    )


def test_public_exports() -> None:
    exports = nlp_model.__all__

    assert isinstance(exports, list)
    assert exports, "__all__ must not be empty."

    assert len(exports) == len(set(exports)), (
        "__all__ contains duplicate names."
    )

    missing = [
        name
        for name in exports
        if not hasattr(nlp_model, name)
    ]

    assert not missing, (
        f"Missing public exports: {missing}"
    )

    print(f"PUBLIC EXPORTS: OK ({len(exports)} names)")


def test_json_schema() -> None:
    schemas = {
        "NLPDocument": NLPDocument.model_json_schema(),
        "NLPAnalysis": NLPAnalysis.model_json_schema(),
    }

    expected_required = {
        "NLPDocument": {
            "document_id",
            "source",
        },
        "NLPAnalysis": {
            "analysis_id",
            "document_id",
            "text_version_id",
        },
    }

    for model_name, schema in schemas.items():
        assert isinstance(schema, dict)

        assert schema.get("type") == "object", (
            f"{model_name}: expected object schema."
        )

        properties = schema.get("properties", {})
        required = set(schema.get("required", []))

        assert expected_required[model_name].issubset(required), (
            f"{model_name}: missing required fields. "
            f"Expected {expected_required[model_name]}, "
            f"got {required}"
        )

        assert properties, (
            f"{model_name}: schema has no properties."
        )

        # Sprawdzenie, czy schemat można zapisać jako JSON.
        serialized_schema = json.dumps(
            schema,
            ensure_ascii=False,
        )

        restored_schema = json.loads(serialized_schema)

        assert restored_schema == schema

        print(
            f"JSON SCHEMA {model_name}: OK "
            f"({len(properties)} properties)"
        )

        # Schematy powinny zawierać definicje typów zagnieżdżonych.
        definitions = schema.get("$defs", {})

        assert isinstance(definitions, dict)

        print(
            f"  Nested definitions: {len(definitions)}"
        )


def test_document_serialization() -> None:
    original = build_document()

    json_data = original.model_dump_json(
        indent=2,
    )

    assert isinstance(json_data, str)

    decoded = json.loads(json_data)

    assert decoded["document_id"] == DOCUMENT_ID
    assert decoded["source"]["source_id"] == "source-001"

    restored = NLPDocument.model_validate_json(json_data)

    assert restored == original

    assert restored.text_versions[0].text == TEXT
    assert restored.text_versions[0].language.language_code == "pl"

    print("NLPDocument SERIALIZATION: OK")
    print("NLPDocument ROUND-TRIP: OK")


def test_analysis_serialization() -> None:
    original = build_analysis()

    json_data = original.model_dump_json(
        indent=2,
    )

    assert isinstance(json_data, str)

    decoded = json.loads(json_data)

    assert decoded["analysis_id"] == "analysis-001"
    assert decoded["provider"]["provider_id"] == "test-provider"
    assert len(decoded["tokens"]) == 3

    restored = NLPAnalysis.model_validate_json(json_data)

    assert restored == original

    assert restored.status == AnalysisStatus.COMPLETED
    assert restored.tokens[0].text == "Ala"
    assert restored.provider.provider_id == "test-provider"

    print("NLPAnalysis SERIALIZATION: OK")
    print("NLPAnalysis ROUND-TRIP: OK")


def test_invalid_document_json() -> None:
    invalid_json = json.dumps({
        "document_id": DOCUMENT_ID,
        # Brakuje wymaganego pola source.
    })

    try:
        NLPDocument.model_validate_json(invalid_json)
    except ValidationError as exc:
        assert any(
            error["loc"] == ("source",)
            for error in exc.errors()
        )
    else:
        raise AssertionError(
            "NLPDocument accepted JSON without required source."
        )

    print("NLPDocument INVALID JSON REJECTION: OK")


def test_invalid_analysis_json() -> None:
    invalid_json = json.dumps({
        "analysis_id": "analysis-invalid",
        "document_id": DOCUMENT_ID,
        # Brakuje wymaganego text_version_id.
    })

    try:
        NLPAnalysis.model_validate_json(invalid_json)
    except ValidationError as exc:
        assert any(
            error["loc"] == ("text_version_id",)
            for error in exc.errors()
        )
    else:
        raise AssertionError(
            "NLPAnalysis accepted JSON without required text_version_id."
        )

    print("NLPAnalysis INVALID JSON REJECTION: OK")


def main() -> None:
    tests = [
        test_public_exports,
        test_json_schema,
        test_document_serialization,
        test_analysis_serialization,
        test_invalid_document_json,
        test_invalid_analysis_json,
    ]

    failures = []

    print("=" * 60)
    print("NLP MODEL CONTRACT TESTS")
    print("=" * 60)

    for test in tests:
        try:
            test()
        except Exception as exc:
            failures.append((test.__name__, exc))

            print(f"\nFAILED: {test.__name__}")
            print(f"{type(exc).__name__}: {exc}")

    print("\n" + "=" * 60)

    if failures:
        print(
            f"CONTRACT TESTS FAILED: "
            f"{len(failures)}/{len(tests)}"
        )

        for name, exc in failures:
            print(
                f"- {name}: {type(exc).__name__}: {exc}"
            )

        raise SystemExit(1)

    print(
        f"ALL CONTRACT TESTS PASSED: "
        f"{len(tests)}/{len(tests)}"
    )


if __name__ == "__main__":
    main()


