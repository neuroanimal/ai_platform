
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NLP JSON SCHEMA TESTS

Zakres:
    1. Kontrola struktury JSON Schema.
    2. Kontrola wymaganych pól.
    3. Kontrola referencji $ref i $defs.
    4. Wykrywanie kolizji definicji.
    5. Budowanie wspólnego pakietu NLPDocument + NLPAnalysis.
    6. Test powtarzalności generowania.
    7. Eksport schematów do plików JSON.
    8. Kontrola przykładów przez modele Pydantic.

Bez dodatkowych zależności.
"""

import json
from pathlib import Path
from urllib.parse import unquote

from ai_platform.common.nlp.model import (
    NLPAnalysis,
    NLPDocument,
    SourceDescriptor,
)


ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = (
    ROOT
    / "config"
    / "test_env"
    / "generated_schemas"
)

DOCUMENT_SCHEMA_PATH = (
    OUTPUT_DIR / "nlp_document.schema.json"
)

ANALYSIS_SCHEMA_PATH = (
    OUTPUT_DIR / "nlp_analysis.schema.json"
)

BUNDLE_SCHEMA_PATH = (
    OUTPUT_DIR / "nlp_bundle.schema.json"
)


def canonical_json(data: dict) -> str:
    """Deterministyczna reprezentacja JSON."""

    return json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def build_schemas() -> dict[str, dict]:
    """Generuje schematy modeli NLP."""

    return {
        "NLPDocument": NLPDocument.model_json_schema(),
        "NLPAnalysis": NLPAnalysis.model_json_schema(),
    }


def resolve_json_pointer(
    document: dict,
    reference: str,
):
    """Rozwiązuje lokalny JSON Pointer."""

    assert reference.startswith("#/"), (
        f"Unsupported JSON reference: {reference}"
    )

    current = document

    pointer = unquote(reference[2:])

    for raw_part in pointer.split("/"):
        part = (
            raw_part
            .replace("~1", "/")
            .replace("~0", "~")
        )

        assert isinstance(current, dict), (
            f"Invalid JSON pointer parent for {reference}"
        )

        assert part in current, (
            f"Unresolved JSON reference: {reference}"
        )

        current = current[part]

    return current


def collect_references(value, references: list[str]) -> None:
    """Rekurencyjnie zbiera wszystkie pola $ref."""

    if isinstance(value, dict):
        if "$ref" in value:
            references.append(value["$ref"])

        for child in value.values():
            collect_references(child, references)

    elif isinstance(value, list):
        for child in value:
            collect_references(child, references)


def validate_references(schema: dict) -> int:
    """Sprawdza, czy wszystkie lokalne referencje są rozwiązywalne."""

    references: list[str] = []

    collect_references(schema, references)

    for reference in references:
        resolve_json_pointer(schema, reference)

    return len(references)


def merge_definitions(
    schemas: dict[str, dict],
) -> dict:
    """
    Łączy definicje schematów.

    Identyczne definicje o tej samej nazwie są współdzielone.
    Różne definicje o tej samej nazwie powodują błąd.
    """

    merged = {}

    for schema_name, schema in schemas.items():
        definitions = schema.get("$defs", {})

        assert isinstance(definitions, dict), (
            f"{schema_name}: $defs must be a dictionary."
        )

        for definition_name, definition in definitions.items():

            if definition_name in merged:
                existing = canonical_json(
                    merged[definition_name]
                )

                incoming = canonical_json(definition)

                assert existing == incoming, (
                    "Definition collision: "
                    f"{definition_name!r} "
                    f"(source: {schema_name})"
                )

            else:
                merged[definition_name] = definition

    return merged


def build_bundle(
    schemas: dict[str, dict],
) -> dict:
    """Buduje wspólny pakiet schematów NLP."""

    definitions = merge_definitions(schemas)

    # Schematy główne stają się definicjami pakietu.
    for schema_name, schema in schemas.items():

        assert schema_name not in definitions, (
            f"Root schema name collides with $defs: {schema_name}"
        )

        root_definition = {
            key: value
            for key, value in schema.items()
            if key not in ("$defs", "$schema")
        }

        definitions[schema_name] = root_definition

    return {
        "title": "NLP Canonical Model Bundle",
        "description": (
            "Combined JSON Schema package for canonical NLP models."
        ),
        "oneOf": [
            {
                "$ref": "#/$defs/NLPDocument",
            },
            {
                "$ref": "#/$defs/NLPAnalysis",
            },
        ],
        "$defs": definitions,
    }


def build_document_example() -> NLPDocument:
    return NLPDocument(
        document_id="document-schema-test",
        source=SourceDescriptor(
            source_id="source-schema-test",
            source_type="text",
            title="JSON Schema test",
        ),
        title="Test document",
    )


def build_analysis_example() -> NLPAnalysis:
    return NLPAnalysis(
        analysis_id="analysis-schema-test",
        document_id="document-schema-test",
        text_version_id="version-schema-test",
    )


def test_schema_structure(
    schemas: dict[str, dict],
) -> None:

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

    for name, schema in schemas.items():

        assert schema.get("type") == "object", (
            f"{name}: root type must be object."
        )

        assert isinstance(schema.get("properties"), dict)

        required = set(schema.get("required", []))

        assert expected_required[name].issubset(required), (
            f"{name}: missing required fields: "
            f"{expected_required[name] - required}"
        )

        assert isinstance(schema.get("$defs"), dict)

        print(
            f"SCHEMA STRUCTURE {name}: OK "
            f"({len(schema['properties'])} properties)"
        )


def test_schema_references(
    schemas: dict[str, dict],
) -> None:

    for name, schema in schemas.items():

        count = validate_references(schema)

        print(
            f"SCHEMA REFERENCES {name}: OK "
            f"({count} references)"
        )


def test_definition_merge(
    schemas: dict[str, dict],
) -> None:

    definitions = merge_definitions(schemas)

    assert definitions

    print(
        "DEFINITION MERGE: OK "
        f"({len(definitions)} definitions)"
    )


def test_bundle(
    schemas: dict[str, dict],
    bundle: dict,
) -> None:

    assert bundle.get("title") == "NLP Canonical Model Bundle"

    assert len(bundle.get("oneOf", [])) == 2

    assert "NLPDocument" in bundle["$defs"]
    assert "NLPAnalysis" in bundle["$defs"]

    count = validate_references(bundle)

    print(
        "BUNDLE SCHEMA: OK "
        f"({len(bundle['$defs'])} definitions, "
        f"{count} references)"
    )


def test_deterministic_generation(
    schemas: dict[str, dict],
) -> None:

    regenerated = build_schemas()

    for name in schemas:

        first = canonical_json(schemas[name])
        second = canonical_json(regenerated[name])

        assert first == second, (
            f"{name}: schema generation is not deterministic."
        )

    first_bundle = canonical_json(
        build_bundle(schemas)
    )

    second_bundle = canonical_json(
        build_bundle(regenerated)
    )

    assert first_bundle == second_bundle

    print("DETERMINISTIC GENERATION: OK")


def test_pydantic_examples() -> None:

    document = build_document_example()
    analysis = build_analysis_example()

    document_json = document.model_dump_json()
    analysis_json = analysis.model_dump_json()

    restored_document = NLPDocument.model_validate_json(
        document_json
    )

    restored_analysis = NLPAnalysis.model_validate_json(
        analysis_json
    )

    assert restored_document == document
    assert restored_analysis == analysis

    print("PYDANTIC DOCUMENT EXAMPLE: OK")
    print("PYDANTIC ANALYSIS EXAMPLE: OK")


def test_schema_export(
    schemas: dict[str, dict],
    bundle: dict,
) -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    outputs = {
        DOCUMENT_SCHEMA_PATH: schemas["NLPDocument"],
        ANALYSIS_SCHEMA_PATH: schemas["NLPAnalysis"],
        BUNDLE_SCHEMA_PATH: bundle,
    }

    for path, schema in outputs.items():

        serialized = json.dumps(
            schema,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

        path.write_text(
            serialized + "\n",
            encoding="utf-8",
        )

        restored = json.loads(
            path.read_text(encoding="utf-8")
        )

        assert restored == schema

        print(
            f"SCHEMA EXPORT: OK "
            f"{path.relative_to(ROOT)}"
        )


def main() -> None:

    schemas = build_schemas()
    bundle = build_bundle(schemas)

    tests = [
        (
            "SCHEMA STRUCTURE",
            lambda: test_schema_structure(schemas),
        ),
        (
            "SCHEMA REFERENCES",
            lambda: test_schema_references(schemas),
        ),
        (
            "DEFINITION MERGE",
            lambda: test_definition_merge(schemas),
        ),
        (
            "BUNDLE",
            lambda: test_bundle(schemas, bundle),
        ),
        (
            "DETERMINISM",
            lambda: test_deterministic_generation(schemas),
        ),
        (
            "PYDANTIC EXAMPLES",
            test_pydantic_examples,
        ),
        (
            "SCHEMA EXPORT",
            lambda: test_schema_export(schemas, bundle),
        ),
    ]

    failures = []

    print("=" * 60)
    print("NLP JSON SCHEMA TESTS")
    print("=" * 60)

    for name, test in tests:

        try:
            test()

        except Exception as exc:

            failures.append((name, exc))

            print(f"\nFAILED: {name}")
            print(
                f"{type(exc).__name__}: {exc}"
            )

    print("\n" + "=" * 60)

    if failures:

        print(
            f"JSON SCHEMA TESTS FAILED: "
            f"{len(failures)}/{len(tests)}"
        )

        for name, exc in failures:
            print(
                f"- {name}: "
                f"{type(exc).__name__}: {exc}"
            )

        raise SystemExit(1)

    print(
        f"ALL JSON SCHEMA TESTS PASSED: "
        f"{len(tests)}/{len(tests)}"
    )

    print(f"\nOUTPUT DIRECTORY: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()


