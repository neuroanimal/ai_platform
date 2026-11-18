
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TEST 30A v4
Automatyczny screening jakości odpowiedzi z kolejnych testów.

Wejście:
    results/test_XX_quality.json

Wyjście:
    results/test_XX_analysis_v4.json

Zasady:
- brak zapytań do modeli;
- brak modyfikacji raportu źródłowego;
- heurystyki nie są traktowane jako ostateczna ocena merytoryczna;
- nieobsługiwane zadania trafiają do manual_review.
"""

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"


def normalize(text):
    text = str(text or "").lower()
    text = text.replace(",", ".")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def count_values(records, path):
    values = []

    for record in records:
        value = record

        for key in path:
            value = value.get(key, {}) if isinstance(value, dict) else {}

        if value:
            values.append(str(value))

    return dict(Counter(values))


def technical_completeness(record):
    finish_reason = str(record.get("finish_reason", "")).lower()

    if finish_reason == "length":
        return {
            "status": "truncated",
            "evidence": "finish_reason=length",
        }

    if finish_reason == "stop":
        return {
            "status": "not_marked_truncated",
            "evidence": "finish_reason=stop",
        }

    return {
        "status": "unknown",
        "evidence": f"finish_reason={finish_reason or 'missing'}",
    }


def check_multiplication(answer, expected):
    text = normalize(answer)
    expected = normalize(expected)

    if not expected:
        return "manual_review", "Brak wartości oczekiwanej."

    expected_number = re.escape(expected)
    has_expected = bool(
        re.search(rf"(?<!\d){expected_number}(?!\d)", text)
    )

    # Sprawdzamy, czy model pokazał rozbicie mnożenia
    # na części, a nie tylko przepisał wynik.
    has_partial_products = (
        bool(re.search(r"17\s*[*x×]\s*3\s*=\s*51", text))
        and bool(re.search(r"17\s*[*x×]\s*20\s*=\s*340", text))
        and bool(re.search(r"51\s*\+\s*340\s*=\s*391", text))
    )

    if has_expected and has_partial_products:
        return (
            "candidate_correct_with_calculation",
            "Wynik oczekiwany i rozbicie mnożenia wykryte."
        )

    if has_expected:
        return (
            "candidate_correct_result_only",
            "Wynik oczekiwany występuje, ale pełne obliczenie "
            "nie zostało wykryte."
        )

    if re.search(r"\d+\s*[*x×]\s*\d+\s*=", text):
        return (
            "candidate_incorrect",
            "Wykryto działanie mnożenia, ale brak wyniku oczekiwanego."
        )

    return "manual_review", "Nie udało się wiarygodnie ocenić mnożenia."


def check_percentage(answer, expected):
    text = normalize(answer)

    expected_match = re.search(
        r"(\d+(?:\.\d+)?)\s*%",
        str(expected)
    )

    if not expected_match:
        return "manual_review", "Nieobsługiwany format wartości oczekiwanej."

    expected_value = float(expected_match.group(1))

    found = [
        float(value)
        for value in re.findall(r"(\d+(?:\.\d+)?)\s*%", text)
    ]

    if not found:
        return "manual_review", "Nie wykryto wartości procentowej."

    if any(abs(value - expected_value) < 0.0001 for value in found):
        if any(abs(value - expected_value) >= 0.0001 for value in found):
            return (
                "manual_review",
                "Występują różne wartości procentowe; możliwa sprzeczność."
            )

        return (
            "candidate_correct",
            f"Wykryto oczekiwaną wartość {expected_value:g}%."
        )

    return (
        "candidate_incorrect",
        f"Oczekiwano {expected_value:g}%, wykryto: {found}."
    )


def check_syllogism(answer, language):
    text = normalize(answer)

    positive = (
        bool(re.search(r"\btak\b", text))
        if language == "pl"
        else bool(re.search(r"\byes\b", text))
    )

    negative = (
        bool(re.search(r"\bnie\b", text))
        if language == "pl"
        else bool(re.search(r"\bno\b", text))
    )

    if positive and negative:
        return (
            "manual_review",
            "Wykryto zarówno pozytywne, jak i negatywne sformułowania."
        )

    if positive:
        return (
            "candidate_correct_conclusion",
            "Wykryto pozytywną odpowiedź; poprawność uzasadnienia "
            "wymaga osobnej kontroli."
        )

    if negative:
        return (
            "candidate_incorrect_conclusion",
            "Wykryto negatywną odpowiedź; poprawność uzasadnienia "
            "wymaga osobnej kontroli."
        )

    return "manual_review", "Nie wykryto jednoznacznej odpowiedzi."


def check_currency(answer, language):
    text = normalize(answer)

    if language == "pl":
        correct_conclusion = (
            "nie oznacza automatycznie" in text
            or "nie musi oznaczać" in text
        )
        incorrect_conclusion = (
            "oznacza automatycznie wzrost" in text
            and "nie oznacza automatycznie" not in text
        )
    else:
        correct_conclusion = (
            "does not automatically mean" in text
            or "does not necessarily mean" in text
        )
        incorrect_conclusion = (
            "automatically means an increase" in text
            and "does not automatically mean" not in text
        )

    if correct_conclusion:
        return (
            "candidate_correct_conclusion",
            "Wykryto brak automatycznej zależności. "
            "Interpretacja kierunku kursu wymaga kontroli."
        )

    if incorrect_conclusion:
        return (
            "candidate_incorrect_conclusion",
            "Wykryto stwierdzenie o automatycznym wzroście CPI."
        )

    return (
        "manual_review",
        "Nie wykryto jednoznacznego wniosku ekonomicznego."
    )


def assess_answer(record):
    test_id = record.get("test_id", "")
    language = record.get("language", "")
    answer = record.get("answer", "")
    expected = record.get("expected", "")

    if test_id == "arithmetic_multiplication":
        status, evidence = check_multiplication(answer, expected)

    elif test_id == "percentage_change":
        status, evidence = check_percentage(answer, expected)

    elif test_id == "logical_syllogism":
        status, evidence = check_syllogism(answer, language)

    elif test_id == "currency_vs_inflation":
        status, evidence = check_currency(answer, language)

    else:
        status = "manual_review"
        evidence = f"Nieobsługiwany test_id: {test_id}"

    return {
        "status": status,
        "evidence": evidence,
        "is_final_judgement": False,
    }


def detect_repetition(answer):
    sentences = re.split(r"[.!?]\s+", str(answer or ""))
    normalized = [
        normalize(sentence)
        for sentence in sentences
        if len(normalize(sentence)) > 20
    ]

    counts = Counter(normalized)
    repeated = [
        sentence
        for sentence, count in counts.items()
        if count > 1
    ]

    return {
        "status": "repetition_detected" if repeated else "no_repetition_detected",
        "repeated_sentences": repeated[:5],
        "note": (
            "Brak wykrytego powtórzenia nie dowodzi spójności logicznej."
        ),
    }


def analyze_record(record):
    return {
        "model": record.get("model"),
        "test_id": record.get("test_id"),
        "category": record.get("category"),
        "language": record.get("language"),
        "expected": record.get("expected"),
        "answer": record.get("answer"),
        "elapsed_seconds": record.get("elapsed_seconds"),
        "usage": record.get("usage", {}),
        "finish_reason": record.get("finish_reason"),
        "automatic_assessment": {
            "answer_screening": assess_answer(record),
            "technical_completeness": technical_completeness(record),
            "repetition": detect_repetition(record.get("answer", "")),
            "reasoning": {
                "status": "manual_review",
                "note": (
                    "Automatyczny screening nie potwierdza "
                    "poprawności toku rozumowania."
                ),
            },
            "consistency": {
                "status": "manual_review",
                "note": (
                    "Powtórzenia tekstu nie są równoważne "
                    "wykrywaniu sprzeczności logicznych."
                ),
            },
            "language_quality": {
                "status": "manual_review",
                "note": "Ocena jakości języka wymaga osobnej analizy.",
            },
        },
    }


def summarize(records):
    screening = Counter()
    completeness = Counter()
    reasoning = Counter()
    manual_review = 0

    by_model_language = defaultdict(Counter)

    for record in records:
        assessment = record["automatic_assessment"]

        status = assessment["answer_screening"]["status"]
        screening[status] += 1

        completeness[
            assessment["technical_completeness"]["status"]
        ] += 1

        reasoning[
            assessment["reasoning"]["status"]
        ] += 1

        if status == "manual_review":
            manual_review += 1

        key = f'{record["model"]} / {record["language"]}'
        by_model_language[key][status] += 1

    return {
        "records": len(records),
        "answer_screening": dict(screening),
        "technical_completeness": dict(completeness),
        "reasoning": dict(reasoning),
        "manual_review_required": manual_review,
        "by_model_language": {
            key: dict(value)
            for key, value in sorted(by_model_language.items())
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="TEST 30A v4 — automatic test-result screening"
    )

    parser.add_argument(
        "input",
        nargs="?",
        default="results/test_30_bilingual_quality.json",
        help="Ścieżka do surowego raportu testu JSON."
    )

    args = parser.parse_args()

    input_file = (BASE_DIR / args.input).resolve()

    if not input_file.exists():
        raise FileNotFoundError(
            f"Nie znaleziono raportu: {input_file}"
        )

    with input_file.open("r", encoding="utf-8") as f:
        source = json.load(f)

    source_records = source.get("results")

    if not isinstance(source_records, list):
        raise ValueError(
            "Raport nie zawiera listy 'results'."
        )

    analyzed = [
        analyze_record(record)
        for record in source_records
    ]

    output = {
        "test": "TEST 30A v4 — automatic result screening",
        "version": "4.0",
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_file": str(input_file),
        "analysis_method": (
            "deterministic_rule_based_screening_with_manual_review"
        ),
        "policy": {
            "source_report_modified": False,
            "model_requests_performed": False,
            "automatic_screening_is_final_judgement": False,
            "unknown_test_ids_require_manual_review": True,
            "reasoning_is_automatically_certified": False,
        },
        "summary": summarize(analyzed),
        "results": analyzed,
    }

    output_name = f"{input_file.stem}_analysis_v4.json"
    output_file = RESULTS_DIR / output_name

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("=== TEST 30A v4: AUTOMATIC SCREENING ===")
    print(f"Source: {input_file}")
    print(f"Output: {output_file}")
    print(f"Records analyzed: {len(analyzed)}")

    print("\nSUMMARY")
    print(json.dumps(
        output["summary"],
        ensure_ascii=False,
        indent=2
    ))

    print("\nAnalysis completed.")


if __name__ == "__main__":
    main()

