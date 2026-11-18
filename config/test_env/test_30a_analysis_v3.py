
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TEST 30A v3
Rozszerzenie ręcznej klasyfikacji o not_demonstrated.

Źródło:
    results/test_30a_analysis_v2.json

Wynik:
    results/test_30a_analysis_v3.json

Nie wykonuje zapytań do modeli.
Nie modyfikuje v2 ani raportu źródłowego.
"""

import json
from copy import deepcopy
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone


BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"

INPUT_FILE = RESULTS_DIR / "test_30a_analysis_v2.json"
OUTPUT_FILE = RESULTS_DIR / "test_30a_analysis_v3.json"


# Dokładnie te trzy odpowiedzi mają poprawny wynik,
# ale nie pokazują wystarczającego toku obliczeń.
NOT_DEMONSTRATED_CASES = {
    ("qwen25-15b-localai", "pl", "arithmetic_multiplication"),
    ("bielik-15b-localai", "pl", "arithmetic_multiplication"),
    ("bielik-15b-localai", "en", "arithmetic_multiplication"),
}


def count_values(records, getter):
    return dict(Counter(getter(record) for record in records))


def summarize(records):
    overall = {
        "records": len(records),
        "correctness": count_values(
            records,
            lambda r: r["manual_assessment"]["correctness"]
        ),
        "reasoning": count_values(
            records,
            lambda r: r["manual_assessment"]["reasoning"]
        ),
        "consistency": count_values(
            records,
            lambda r: r["manual_assessment"]["consistency"]
        ),
        "technical_completeness": count_values(
            records,
            lambda r: r["technical_metadata"]["completeness"]
        ),
    }

    grouped = defaultdict(list)

    for record in records:
        key = f'{record["model"]} / {record["language"]}'
        grouped[key].append(record)

    by_model_language = {}

    for key, group in sorted(grouped.items()):
        by_model_language[key] = {
            "records": len(group),
            "correctness": count_values(
                group,
                lambda r: r["manual_assessment"]["correctness"]
            ),
            "reasoning": count_values(
                group,
                lambda r: r["manual_assessment"]["reasoning"]
            ),
            "consistency": count_values(
                group,
                lambda r: r["manual_assessment"]["consistency"]
            ),
            "technical_completeness": count_values(
                group,
                lambda r: r["technical_metadata"]["completeness"]
            ),
        }

    return {
        "overall": overall,
        "by_model_language": by_model_language,
    }


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Nie znaleziono pliku wejściowego: {INPUT_FILE}"
        )

    with INPUT_FILE.open("r", encoding="utf-8") as f:
        source = json.load(f)

    output = deepcopy(source)

    changed = []

    for record in output["results"]:
        key = (
            record["model"],
            record["language"],
            record["test_id"],
        )

        if key not in NOT_DEMONSTRATED_CASES:
            continue

        assessment = record["manual_assessment"]

        # Nie zmieniamy correctness ani consistency.
        if assessment["correctness"] != "correct":
            raise ValueError(
                f"Niespodziewana ocena correctness dla: {key}"
            )

        old_reasoning = assessment["reasoning"]

        assessment["reasoning"] = "not_demonstrated"
        assessment["note"] = (
            "Poprawny wynik i równanie, ale bez wystarczającego "
            "rozwinięcia obliczeń, aby ocenić tok rozumowania."
        )

        changed.append({
            "model": record["model"],
            "language": record["language"],
            "test_id": record["test_id"],
            "old_reasoning": old_reasoning,
            "new_reasoning": "not_demonstrated",
        })

    if len(changed) != len(NOT_DEMONSTRATED_CASES):
        raise ValueError(
            "Liczba zmienionych rekordów jest inna niż oczekiwane 3. "
            f"Zmieniono: {len(changed)}"
        )

    output["test"] = "TEST 30A v3 — extended manual classification"
    output["version"] = "3.0"
    output["created_at_utc"] = datetime.now(
        timezone.utc
    ).isoformat()

    output["classification_method"] = (
        "manual_review_with_automated_technical_metadata"
    )

    output["policy"]["reasoning_labels"] = [
        "sound",
        "flawed",
        "mixed",
        "not_demonstrated",
        "manual_review",
    ]

    output["policy"]["v3_changes"] = {
        "added_reasoning_label": "not_demonstrated",
        "changed_records": len(changed),
        "correctness_changed": False,
        "consistency_changed": False,
        "source_v2_modified": False,
    }

    output["summary"] = summarize(output["results"])

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("=== TEST 30A v3: EXTENDED MANUAL CLASSIFICATION ===")
    print(f"Source: {INPUT_FILE}")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Records: {len(output['results'])}")
    print(f"Changed reasoning labels: {len(changed)}")

    for item in changed:
        print(
            f"  {item['model']} / {item['language']} / "
            f"{item['test_id']}: "
            f"{item['old_reasoning']} -> {item['new_reasoning']}"
        )

    print("\nOVERALL")
    print(json.dumps(
        output["summary"]["overall"],
        ensure_ascii=False,
        indent=2
    ))

    print("\nAnalysis completed.")


if __name__ == "__main__":
    main()

