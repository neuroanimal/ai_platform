from pathlib import Path

script = r'''#!/usr/bin/env python3
"""
TEST 30A v2 — ręczna klasyfikacja jakości odpowiedzi modeli (24 rekordy).

Założenia:
- Źródłowy raport test_30_bilingual_quality.json jest tylko odczytywany.
- Klasyfikacja merytoryczna pochodzi z uzgodnionej ręcznej oceny 24 odpowiedzi.
- Automatyczne metadane (np. finish_reason, tokeny) nie rozstrzygają o poprawności.
- Skrypt tworzy osobny raport: results/test_30a_analysis_v2.json.

Uruchom z katalogu config/test_env:
    python test_30a_analysis_v2.py
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
SOURCE_PATH = BASE_DIR / "results" / "test_30_bilingual_quality.json"
OUTPUT_PATH = BASE_DIR / "results" / "test_30a_analysis_v2.json"

# Klasyfikacja uzgodniona po ręcznym przeglądzie odpowiedzi.
# correctness: correct / partial / incorrect
# reasoning:   sound / flawed / mixed / manual_review
MANUAL_ASSESSMENTS: dict[tuple[str, str, str], dict[str, str]] = {
    ("qwen25-05b-localai", "pl", "arithmetic_multiplication"): {
        "correctness": "partial",
        "reasoning": "flawed",
        "consistency": "contradictory",
        "note": "Wynik 391 pojawia się w odpowiedzi, ale dalsze obliczenia/wyjaśnienie są sprzeczne; odpowiedź jest ucięta.",
    },
    ("qwen25-05b-localai", "pl", "percentage_change"): {
        "correctness": "incorrect",
        "reasoning": "flawed",
        "consistency": "consistent",
        "note": "Model podaje 2% zamiast 12%.",
    },
    ("qwen25-05b-localai", "pl", "logical_syllogism"): {
        "correctness": "incorrect",
        "reasoning": "flawed",
        "consistency": "consistent",
        "note": "Model błędnie zaprzecza, że Mruczek jest ssakiem.",
    },
    ("qwen25-05b-localai", "pl", "currency_vs_inflation"): {
        "correctness": "partial",
        "reasoning": "manual_review",
        "consistency": "mixed",
        "note": "Ogólny wniosek jest zasadniczo poprawny, ale wyjaśnienie jest słabe/niejasne.",
    },

    ("qwen25-05b-localai", "en", "arithmetic_multiplication"): {
        "correctness": "incorrect",
        "reasoning": "flawed",
        "consistency": "consistent",
        "note": "Model błędnie oblicza 17 × 23 (dochodzi do 85).",
    },
    ("qwen25-05b-localai", "en", "percentage_change"): {
        "correctness": "correct",
        "reasoning": "sound",
        "consistency": "consistent",
        "note": "Poprawny wzrost o 12%.",
    },
    ("qwen25-05b-localai", "en", "logical_syllogism"): {
        "correctness": "correct",
        "reasoning": "sound",
        "consistency": "consistent",
        "note": "Poprawny wniosek: Mrruczek jest ssakiem.",
    },
    ("qwen25-05b-localai", "en", "currency_vs_inflation"): {
        "correctness": "correct",
        "reasoning": "sound",
        "consistency": "consistent",
        "note": "Poprawnie wskazuje brak automatycznej zależności oraz możliwy wpływ na ceny importu.",
    },

    ("qwen25-15b-localai", "pl", "arithmetic_multiplication"): {
        "correctness": "correct",
        "reasoning": "sound",
        "consistency": "consistent",
        "note": "Poprawny wynik i rozumowanie.",
    },
    ("qwen25-15b-localai", "pl", "percentage_change"): {
        "correctness": "correct",
        "reasoning": "sound",
        "consistency": "consistent",
        "note": "Poprawny wzrost o 12%.",
    },
    ("qwen25-15b-localai", "pl", "logical_syllogism"): {
        "correctness": "incorrect",
        "reasoning": "flawed",
        "consistency": "consistent",
        "note": "Błędny wniosek dotyczący przynależności Mruczka do ssaków.",
    },
    ("qwen25-15b-localai", "pl", "currency_vs_inflation"): {
        "correctness": "incorrect",
        "reasoning": "flawed",
        "consistency": "mixed",
        "note": "Błędnie przedstawia wzrost USD/PLN jako automatycznie podnoszący CPI; odpowiedź jest ucięta.",
    },

    ("qwen25-15b-localai", "en", "arithmetic_multiplication"): {
        "correctness": "correct",
        "reasoning": "sound",
        "consistency": "consistent",
        "note": "Poprawny wynik i rozumowanie.",
    },
    ("qwen25-15b-localai", "en", "percentage_change"): {
        "correctness": "correct",
        "reasoning": "sound",
        "consistency": "consistent",
        "note": "Poprawny wzrost o 12%.",
    },
    ("qwen25-15b-localai", "en", "logical_syllogism"): {
        "correctness": "correct",
        "reasoning": "sound",
        "consistency": "consistent",
        "note": "Poprawny wniosek: Mrruczek jest ssakiem.",
    },
    ("qwen25-15b-localai", "en", "currency_vs_inflation"): {
        "correctness": "partial",
        "reasoning": "flawed",
        "consistency": "mixed",
        "note": "Poprawny brak automatycznej zależności, ale błędny kierunek interpretacji wzrostu USD/PLN.",
    },

    ("bielik-15b-localai", "pl", "arithmetic_multiplication"): {
        "correctness": "correct",
        "reasoning": "sound",
        "consistency": "consistent",
        "note": "Poprawny wynik i rozumowanie.",
    },
    ("bielik-15b-localai", "pl", "percentage_change"): {
        "correctness": "correct",
        "reasoning": "sound",
        "consistency": "consistent",
        "note": "Poprawny wzrost o 12%.",
    },
    ("bielik-15b-localai", "pl", "logical_syllogism"): {
        "correctness": "correct",
        "reasoning": "sound",
        "consistency": "consistent",
        "note": "Poprawny wniosek: Mruczek jest ssakiem.",
    },
    ("bielik-15b-localai", "pl", "currency_vs_inflation"): {
        "correctness": "partial",
        "reasoning": "flawed",
        "consistency": "mixed",
        "note": "Ogólny wniosek jest poprawny, ale interpretacja kierunku zmian kursu jest błędna/sprzeczna.",
    },

    ("bielik-15b-localai", "en", "arithmetic_multiplication"): {
        "correctness": "correct",
        "reasoning": "sound",
        "consistency": "consistent",
        "note": "Poprawny wynik i rozumowanie.",
    },
    ("bielik-15b-localai", "en", "percentage_change"): {
        "correctness": "correct",
        "reasoning": "sound",
        "consistency": "consistent",
        "note": "Poprawny wzrost o 12%.",
    },
    ("bielik-15b-localai", "en", "logical_syllogism"): {
        "correctness": "correct",
        "reasoning": "sound",
        "consistency": "consistent",
        "note": "Poprawny wniosek: Mrruczek jest ssakiem.",
    },
    ("bielik-15b-localai", "en", "currency_vs_inflation"): {
        "correctness": "partial",
        "reasoning": "flawed",
        "consistency": "mixed",
        "note": "Ogólny wniosek jest poprawny, ale interpretacja kierunku zmian kursu jest błędna.",
    },
}


def load_source() -> dict[str, Any]:
    if not SOURCE_PATH.exists():
        raise FileNotFoundError(
            f"Nie znaleziono raportu źródłowego: {SOURCE_PATH}\n"
            "Uruchom skrypt z katalogu config/test_env lub umieść plik "
            "results/test_30_bilingual_quality.json w tym katalogu."
        )
    with SOURCE_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        raise ValueError("Nieprawidłowy format raportu źródłowego: brak listy 'results'.")
    return data


def classify_completeness(record: dict[str, Any]) -> str:
    # To wyłącznie metadana techniczna, nie ocena poprawności odpowiedzi.
    finish = str(record.get("finish_reason", "")).strip().lower()
    return "truncated" if finish == "length" else "not_marked_truncated"


def make_record(source_index: int, record: dict[str, Any]) -> dict[str, Any]:
    key = (
        str(record.get("model", "")),
        str(record.get("language", "")).lower(),
        str(record.get("test_id", "")),
    )
    assessment = MANUAL_ASSESSMENTS.get(key)
    if assessment is None:
        raise KeyError(
            f"Brak ręcznej klasyfikacji dla rekordu #{source_index}: {key!r}"
        )

    return {
        "source_index": source_index,
        "model": key[0],
        "language": key[1],
        "test_id": key[2],
        "category": record.get("category"),
        "prompt": record.get("prompt"),
        "expected": record.get("expected"),
        "answer": record.get("answer"),
        "elapsed_seconds": record.get("elapsed_seconds"),
        "usage": record.get("usage"),
        "finish_reason": record.get("finish_reason"),
        "technical_metadata": {
            "completeness": classify_completeness(record),
            "completion_tokens": (record.get("usage") or {}).get("completion_tokens"),
            "total_tokens": (record.get("usage") or {}).get("total_tokens"),
        },
        "manual_assessment": {
            **assessment,
            "method": "manual_review",
        },
    }


def count_values(records: list[dict[str, Any]], path: tuple[str, ...]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for record in records:
        value: Any = record
        for part in path:
            value = value.get(part, {}) if isinstance(value, dict) else {}
        if value is not None:
            counter[str(value)] += 1
    return dict(sorted(counter.items()))


def build_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[f"{record['model']} / {record['language']}"].append(record)

    by_model_language: dict[str, Any] = {}
    for group_name, group_records in sorted(grouped.items()):
        by_model_language[group_name] = {
            "records": len(group_records),
            "correctness": count_values(group_records, ("manual_assessment", "correctness")),
            "reasoning": count_values(group_records, ("manual_assessment", "reasoning")),
            "consistency": count_values(group_records, ("manual_assessment", "consistency")),
            "technical_completeness": count_values(group_records, ("technical_metadata", "completeness")),
        }

    overall = {
        "records": len(records),
        "correctness": count_values(records, ("manual_assessment", "correctness")),
        "reasoning": count_values(records, ("manual_assessment", "reasoning")),
        "consistency": count_values(records, ("manual_assessment", "consistency")),
        "technical_completeness": count_values(records, ("technical_metadata", "completeness")),
    }

    return {
        "overall": overall,
        "by_model_language": by_model_language,
    }


def main() -> None:
    source = load_source()
    source_records = source["results"]

    if len(source_records) != 24:
        raise ValueError(
            f"Oczekiwano 24 odpowiedzi w raporcie Test 30, znaleziono {len(source_records)}. "
            "Nie tworzę raportu, aby uniknąć niepełnej lub niezgodnej klasyfikacji."
        )

    records = [make_record(i, row) for i, row in enumerate(source_records)]
    seen = {
        (r["model"], r["language"], r["test_id"])
        for r in records
    }
    if len(seen) != 24:
        raise ValueError(
            "W raporcie źródłowym występują powtórzone kombinacje model/język/test "
            "albo brakuje któregoś rekordu."
        )

    missing = set(MANUAL_ASSESSMENTS) - seen
    extra = seen - set(MANUAL_ASSESSMENTS)
    if missing or extra:
        raise ValueError(
            f"Niezgodność zestawu klasyfikacji. Brakujące: {sorted(missing)}; "
            f"nieoczekiwane: {sorted(extra)}"
        )

    report = {
        "test": "TEST 30A v2 — manual answer classification",
        "version": "2.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": str(SOURCE_PATH.relative_to(BASE_DIR)),
        "classification_method": "manual_review_with_automated_technical_metadata",
        "policy": {
            "source_report_modified": False,
            "model_requests_performed": False,
            "automated_metadata_is_not_a_correctness_judge": True,
            "correctness_labels": ["correct", "partial", "incorrect"],
            "reasoning_labels": ["sound", "flawed", "mixed", "manual_review"],
        },
        "summary": build_summary(records),
        "results": records,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("=== TEST 30A v2: MANUAL CLASSIFICATION ===")
    print(f"Source: {SOURCE_PATH}")
    print(f"Output: {OUTPUT_PATH}")
    print(f"Records classified: {len(records)}")
    print("\nOVERALL")
    for dimension, values in report["summary"]["overall"].items():
        if dimension == "records":
            continue
        print(f"  {dimension}: {values}")
    print("\nBY MODEL / LANGUAGE")
    for group, values in report["summary"]["by_model_language"].items():
        print(f"\n{group} ({values['records']} records)")
        for dimension in ("correctness", "reasoning", "consistency", "technical_completeness"):
            print(f"  {dimension}: {values[dimension]}")
    print("\nReport created. The source report was not modified.")


if __name__ == "__main__":
    main()
'''

path = Path("test_30a_analysis_v2.py")
path.write_text(script, encoding="utf-8")
compile(script, str(path), "exec")
print(f"Created and syntax-checked: {path} ({len(script.splitlines())} lines)")

