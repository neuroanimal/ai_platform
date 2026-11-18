
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

    try:
        expected_value = int(expected)
    except ValueError:
        return "manual_review", "Nieobsługiwany format wyniku oczekiwanego."

    expected_pattern = rf"(?<!\d){expected_value}(?!\d)"
    has_expected = bool(re.search(expected_pattern, text))

    # Wykrywanie zapisu działania 17 * 23 = 391.
    direct_operation = re.search(
        r"17\s*[*x×]\s*23\s*=\s*(\d+)",
        text
    )

    if direct_operation:
        calculated_value = int(direct_operation.group(1))
        if calculated_value != expected_value:
            return (
                "candidate_incorrect",
                f"Wykryto działanie 17 × 23 = {calculated_value}, "
                f"oczekiwano {expected_value}."
            )

    # Wykrywanie alternatywnych rozbić mnożenia:
    # a * (b + c), (a * b) + (a * c), itp.
    calculation_patterns = [
        r"17\s*[*x×]\s*20\s*=\s*340",
        r"17\s*[*x×]\s*3\s*=\s*51",
        r"20\s*[*x×]\s*17\s*=\s*340",
        r"3\s*[*x×]\s*17\s*=\s*51",
        r"10\s*[*x×]\s*23\s*=\s*230",
        r"7\s*[*x×]\s*23\s*=\s*161",
        r"17\s*[*x×]\s*20\s*\+\s*17\s*[*x×]\s*3",
        r"17\s*[*x×]\s*3\s*\+\s*17\s*[*x×]\s*20",
        r"10\s*[*x×]\s*23\s*\+\s*7\s*[*x×]\s*23",
        r"7\s*[*x×]\s*23\s*\+\s*10\s*[*x×]\s*23",
    ]

    has_calculation = any(
        re.search(pattern, text)
        for pattern in calculation_patterns
    )

    if has_expected and has_calculation:
        return (
            "candidate_correct_with_calculation",
            "Wykryto oczekiwany wynik i rozpoznawalny sposób obliczenia."
        )

    if has_expected:
        return (
            "candidate_correct_result_only",
            "Wykryto oczekiwany wynik, ale nie potwierdzono poprawnego "
            "wyprowadzenia obliczenia."
        )

    if direct_operation:
        return (
            "candidate_incorrect",
            "Wynik bezpośredniego działania jest niezgodny z oczekiwanym."
        )

    return (
        "manual_review",
        "Nie udało się wiarygodnie ocenić mnożenia."
    )


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

    unique_values = sorted(set(found))

    if len(unique_values) > 1:
        return (
            "manual_review",
            f"Wykryto różne wartości procentowe: {unique_values}. "
            "Możliwa sprzeczność lub wartości pośrednie."
        )

    if abs(unique_values[0] - expected_value) < 0.0001:
        return (
            "candidate_correct",
            f"Wykryto oczekiwaną wartość {expected_value:g}%."
        )

    return (
        "candidate_incorrect",
        f"Oczekiwano {expected_value:g}%, wykryto: {unique_values}."
    )


def check_syllogism(answer, language):
    text = normalize(answer)

    if language == "pl":
        subject_pattern = r"\bmruczek\b"
        predicate_pattern = (
            r"(?:jest\s+ssakiem|"
            r"należy\s+do\s+ssaków|"
            r"jest\s+przedstawicielem\s+ssaków)"
        )
        negation_pattern = r"\bnie\b|\bnigdy\b"

    elif language == "en":
        subject_pattern = r"\bmrruczek\b"
        predicate_pattern = (
            r"(?:is\s+(?:not\s+)?(?:a\s+)?mammal|"
            r"isn't\s+(?:a\s+)?mammal|"
            r"belongs\s+to\s+the\s+mammals)"
        )
        negation_pattern = r"\bnot\b|\bnever\b|\bisn't\b"

    else:
        return (
            "manual_review",
            f"Nieobsługiwany język: {language}."
        )

    pattern = re.compile(
        rf"{subject_pattern}[^.!?]{{0,100}}?{predicate_pattern}",
        re.IGNORECASE
    )

    assertions = []

    for match in pattern.finditer(text):
        statement = match.group(0)

        is_negative = bool(
            re.search(negation_pattern, statement)
        )

        assertions.append(
            "negative" if is_negative else "positive"
        )

    has_positive = "positive" in assertions
    has_negative = "negative" in assertions

    if has_positive and has_negative:
        return (
            "manual_review",
            "Wykryto zarówno pozytywne, jak i negatywne "
            "przypisanie cechy ssaka temu samemu obiektowi."
        )

    if has_positive:
        return (
            "candidate_correct_conclusion",
            "Wykryto stwierdzenie, że badany obiekt jest ssakiem. "
            "Poprawność uzasadnienia wymaga osobnej kontroli."
        )

    if has_negative:
        return (
            "candidate_incorrect_conclusion",
            "Wykryto zaprzeczenie, że badany obiekt jest ssakiem."
        )

    return (
        "manual_review",
        "Nie wykryto jednoznacznego przypisania ani zaprzeczenia "
        "cechy ssaka w kontekście badanego obiektu."
    )


def check_currency(answer, language):
    text = normalize(answer)

    if language == "pl":
        correct_conclusion_patterns = [
            r"nie oznacza(?: to)? automatycznie",
            r"nie musi oznaczać",
            r"nie powoduje automatycznie",
            r"nie wynika automatycznie",
            r"nie prowadzi automatycznie do",
        ]

        incorrect_conclusion_patterns = [
            r"(?<!nie )automatycznie\s+(?:powoduje|oznacza|prowadzi do)\s+wzrost(?:u)?",
            r"(?<!nie )(?:oznacza|powoduje)\s+automatycznie\s+wzrost(?:u)?",
            r"zawsze powoduje wzrost",
            r"musi prowadzi[ć]+do wzrost(?:u)?",
        ]

        correct_direction_patterns = [
            r"(?:usd|dolar)[^.!?]{0,100}(?:drożej|więcej\s+złotych|kosztuje\s+więcej\s+pln)",
            r"(?:złoty|pln)[^.!?]{0,100}(?:słabnie|osłabia\s+się|traci\s+na\s+wartości)",
            r"(?:osłabienie|deprecjacja)\s+(?:złotego|pln)",
            r"za\s+dolara[^.!?]{0,50}więcej\s+złotych",
        ]

        incorrect_direction_patterns = [
            r"(?:złoty|pln)[^.!?]{0,100}(?:umacnia\s+się|zyskuje\s+na\s+wartości)",
            r"(?:usd|dolar)[^.!?]{0,100}(?:tanieje|kosztuje\s+mniej\s+złotych)",
            r"(?:osłabienie|deprecjacja)\s+(?:dolara|usd)",
            r"(?:złoty|pln)[^.!?]{0,100}(?:jest\s+silniejszy|staje\s+się\s+silniejszy)",
        ]

    elif language == "en":
        correct_conclusion_patterns = [
            r"does not automatically mean",
            r"does not necessarily mean",
            r"does not automatically cause",
            r"does not necessarily cause",
        ]

        incorrect_conclusion_patterns = [
            r"automatically means an increase",
            r"automatically causes an increase",
            r"always causes an increase",
            r"must lead to an increase",
        ]

        correct_direction_patterns = [
            r"(?:usd|dollar)[^.!?]{0,100}(?:more expensive|costs more|higher in pln)",
            r"(?:pln|zloty|złoty)[^.!?]{0,100}(?:weakens|depreciates|loses value)",
            r"(?:weakening|depreciation)\s+of\s+(?:the\s+)?(?:pln|zloty)",
            r"more\s+zloty[^.!?]{0,50}(?:per|for)\s+(?:one\s+)?dollar",
        ]

        incorrect_direction_patterns = [
            r"(?:pln|zloty|złoty)[^.!?]{0,100}(?:strengthens|appreciates|gains value)",
            r"(?:usd|dollar)[^.!?]{0,100}(?:becomes cheaper|costs less)",
            r"(?:weakening|depreciation)\s+of\s+(?:the\s+)?(?:usd|dollar)",
            r"(?:pln|zloty|złoty)[^.!?]{0,100}(?:becomes stronger|is stronger)",
        ]

    else:
        return (
            "manual_review",
            f"Nieobsługiwany język: {language}."
        )

    def contains_any(patterns):
        return any(
            re.search(pattern, text)
            for pattern in patterns
        )

    conclusion_correct = contains_any(
        correct_conclusion_patterns
    )

    conclusion_incorrect = contains_any(
        incorrect_conclusion_patterns
    )

    direction_correct = contains_any(
        correct_direction_patterns
    )

    direction_incorrect = contains_any(
        incorrect_direction_patterns
    )

    if conclusion_correct and conclusion_incorrect:
        return (
            "manual_review",
            "Wykryto sprzeczne stwierdzenia dotyczące zależności "
            "między kursem walutowym a CPI."
        )

    if direction_correct and direction_incorrect:
        return (
            "manual_review",
            "Wykryto sprzeczne interpretacje kierunku zmiany kursu."
        )

    if conclusion_incorrect:
        return (
            "candidate_incorrect_conclusion",
            "Odpowiedź sugeruje automatyczny wzrost CPI "
            "w następstwie zmiany kursu."
        )

    if not conclusion_correct:
        return (
            "manual_review",
            "Nie wykryto jednoznacznego stwierdzenia o braku "
            "automatycznej zależności między kursem a CPI."
        )

    if direction_incorrect:
        return (
            "candidate_partial_direction_error",
            "Wniosek o braku automatycznej zależności jest poprawny, "
            "ale wykryto błędną interpretację kierunku USD/PLN."
        )

    if direction_correct:
        return (
            "candidate_correct_conclusion",
            "Wykryto poprawny wniosek o braku automatycznej zależności "
            "oraz poprawną interpretację wzrostu USD/PLN."
        )

    return (
        "candidate_correct_conclusion_direction_not_assessed",
        "Wykryto poprawny wniosek o braku automatycznej zależności, "
        "ale nie wykryto jednoznacznej interpretacji kierunku USD/PLN."
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
    consistency = Counter()
    language_quality = Counter()

    answer_manual_review = 0
    reasoning_manual_review = 0
    consistency_manual_review = 0
    language_manual_review = 0
    records_requiring_human_review = 0

    by_model_language = defaultdict(Counter)

    for record in records:
        assessment = record["automatic_assessment"]

        answer_status = assessment["answer_screening"]["status"]
        technical_status = assessment["technical_completeness"]["status"]
        reasoning_status = assessment["reasoning"]["status"]
        consistency_status = assessment["consistency"]["status"]
        language_status = assessment["language_quality"]["status"]

        screening[answer_status] += 1
        completeness[technical_status] += 1
        reasoning[reasoning_status] += 1
        consistency[consistency_status] += 1
        language_quality[language_status] += 1

        needs_human_review = False

        if answer_status == "manual_review":
            answer_manual_review += 1
            needs_human_review = True

        if reasoning_status == "manual_review":
            reasoning_manual_review += 1
            needs_human_review = True

        if consistency_status == "manual_review":
            consistency_manual_review += 1
            needs_human_review = True

        if language_status == "manual_review":
            language_manual_review += 1
            needs_human_review = True

        if needs_human_review:
            records_requiring_human_review += 1

        key = f'{record["model"]} / {record["language"]}'
        by_model_language[key][answer_status] += 1

    return {
        "records": len(records),

        "answer_screening": dict(screening),
        "technical_completeness": dict(completeness),
        "reasoning": dict(reasoning),
        "consistency": dict(consistency),
        "language_quality": dict(language_quality),

        "human_review": {
            "answer_screening_manual_review_required": answer_manual_review,
            "reasoning_manual_review_required": reasoning_manual_review,
            "consistency_manual_review_required": consistency_manual_review,
            "language_quality_manual_review_required": language_manual_review,
            "total_records_requiring_human_review": records_requiring_human_review,
        },

        "by_model_language": {
            key: dict(value)
            for key, value in sorted(by_model_language.items())
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="TEST 30A v4.1 — automatic test-result screening"
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
        "test": "TEST 30A v4.1 — automatic result screening",
        "version": "4.1",
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

    output_name = f"{input_file.stem}_analysis_v4_1.json"
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

