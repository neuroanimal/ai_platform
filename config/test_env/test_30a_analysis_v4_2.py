#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TEST 30A v4.2
Automatyczny screening jakości odpowiedzi z testu 30 (bilingual quality).

Wejście:
    results/test_30_bilingual_quality*.json   (v1 i v2 raportu)

Wyjście:
    <output-dir>/<stem>_analysis_v4_2.json

Zasady:
- brak zapytań do modeli;
- brak modyfikacji raportu źródłowego;
- heurystyki nie są traktowane jako ostateczna ocena merytoryczna;
- nieobsługiwane zadania trafiają do manual_review.

Zakres (uczciwie): checkery są przypisane do konkretnych test_id
(rejestr CHECKERS). Mnożenie i sylogizm odczytują parametry z promptu
i wartości oczekiwanej, więc działają dla innych liczb i podmiotów.
Kurs walutowy vs CPI jest checkerem tematycznym i nie uogólnia się.

Zmiany względem v4.1:
1. mnożenie: wykrywanie słownych deklaracji wyniku ("equals 85",
   "wynosi 391"), operandy odczytywane z promptu, kontrola kroków
   pośrednich (równań) zamiast listy na sztywno wpisanych rozbić;
2. naprawiony regex "musi prowadzić do wzrostu" (brakowało spacji);
3. odpowiedź ucięta (finish_reason=length) nie dostaje oceny
   "candidate_correct*" - trafia do manual_review z zachowaniem oceny
   wstępnej; błędna teza zapisana przed ucięciem pozostaje błędna;
4. sylogizm: podmiot i orzecznik odczytywane z wartości oczekiwanej;
5. podmiot dopasowywany odpornie na podwojone litery (Mruczek/Mrruczek);
6. obsługa pól run_index z raportu v2 (powtórzenia);
7. jedna stała VERSION dla docstringu, bannera i nazwy pliku wyjściowego.
"""

# pylint: disable=too-many-return-statements

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


VERSION = "4.2"
TITLE = f"TEST 30A v{VERSION}"
VERSION_SUFFIX = "v" + VERSION.replace(".", "_")

BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"

# Operator mnożenia: symbol lub słowo (PL/EN).
MULT_OP = r"(?:[*x×·]|razy|times|multiplied\s+by|pomnożone\s+przez)"

# Czasownik/znak deklarujący wynik działania.
RESULT_VERB = r"(?:=|equals|is|wynosi|daje|to|równa\s+się|gives)"

# Liczba poprzedzona opcjonalnym formatowaniem markdown (np. **391**).
NUMBER_AFTER = r"[\s*]*(\d+)(?![\d])"

# Ogólne równanie arytmetyczne "a op b = c" (kroki pośrednie).
EQUATION = re.compile(
    r"(?<![\d.])(\d+)\s*([*x×·+\-])\s*(\d+)\s*=\s*(\d+)(?![\d])"
)

# Dodatkowe formy orzecznika, których nie da się wyprowadzić
# z samej wartości oczekiwanej (odmiana przez przypadki).
PREDICATE_FORMS = {
    "ssakiem": [
        r"należy\s+do\s+ssaków",
        r"jest\s+przedstawicielem\s+ssaków",
    ],
    "mammal": [
        r"belongs\s+to\s+the\s+mammals",
    ],
}


def normalize(text):
    """Lowercase, unify decimal comma and collapse whitespace."""
    text = str(text or "").lower()
    text = text.replace(",", ".")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def count_values(records, path):
    """Count distinct values found under a nested key path."""
    values = []

    for record in records:
        value = record

        for key in path:
            value = value.get(key, {}) if isinstance(value, dict) else {}

        if value:
            values.append(str(value))

    return dict(Counter(values))


def technical_completeness(record):
    """Classify whether the answer was cut off by the token limit."""
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


def fuzzy_word(word):
    """Build a regex for a word tolerant to doubled letters (Mrruczek)."""
    # Podwojone litery są najpierw zwijane, żeby "mrruczek" i "mruczek"
    # dawały ten sam wzorzec "m+r+u+c+z+e+k+".
    collapsed = re.sub(r"(.)\1+", r"\1", normalize(word))
    letters = [re.escape(ch) + "+" for ch in collapsed if ch.strip()]
    return r"\b" + "".join(letters) + r"\b"


# ============================================================
# MULTIPLICATION
# ============================================================

def extract_operands(prompt):
    """Return (a, b) of the multiplication asked in the prompt, or None."""
    match = re.search(rf"(\d+)\s*{MULT_OP}\s*(\d+)", normalize(prompt))

    if not match:
        return None

    return int(match.group(1)), int(match.group(2))


def find_result_claims(text, operands):
    """Find numbers the answer declares as the result of a x b."""
    claims = []

    if operands:
        a, b = operands
        for left, right in ((a, b), (b, a)):
            pattern = (
                rf"(?<![\d.]){left}\s*{MULT_OP}\s*{right}\s*\)?\s*"
                rf"{RESULT_VERB}{NUMBER_AFTER}"
            )
            claims.extend(int(v) for v in re.findall(pattern, text))

    # Deklaracje wyniku bez powtórzenia działania ("wynik: 391").
    # Liczba nie może rozpoczynać działania ("Wynik: 17 * 23 = 391"
    # nie jest deklaracją wyniku 17).
    generic = (
        r"(?:wynik\w*|result|answer|odpowiedź)\s*"
        r"(?:is|to|jest|wynosi|:|=)?" + NUMBER_AFTER
        + rf"(?!\s*(?:{MULT_OP}|[+\-=]))"
    )
    claims.extend(int(v) for v in re.findall(generic, text))

    return claims


def check_equations(text, operands):
    """Return (correct_steps, wrong_steps) among equations in the text.

    The direct equation a x b = c is not counted as a calculation step,
    because it only restates the result.
    """
    correct_steps = []
    wrong_steps = []

    for left, operator, right, result in EQUATION.findall(text):
        x, y, z = int(left), int(right), int(result)

        if operator in "*x×·":
            value = x * y
            is_direct = operands is not None and {x, y} == set(operands)
        elif operator == "+":
            value = x + y
            is_direct = False
        else:
            value = x - y
            is_direct = False

        step = f"{x} {operator} {y} = {z}"

        if value != z:
            wrong_steps.append(step)
        elif not is_direct:
            correct_steps.append(step)

    return correct_steps, wrong_steps


def check_multiplication(answer, expected, prompt=""):
    """Screen an answer to 'what is a times b'."""
    text = normalize(answer)
    expected = normalize(expected)

    if not expected:
        return "manual_review", "Brak wartości oczekiwanej."

    try:
        expected_value = int(expected)
    except ValueError:
        return "manual_review", "Nieobsługiwany format wyniku oczekiwanego."

    operands = extract_operands(prompt)

    if operands and operands[0] * operands[1] != expected_value:
        return (
            "manual_review",
            f"Niespójna wartość oczekiwana: {operands[0]} × {operands[1]} "
            f"!= {expected_value}."
        )

    claims = find_result_claims(text, operands)
    wrong_claims = sorted({c for c in claims if c != expected_value})
    claims_expected = expected_value in claims

    expected_pattern = rf"(?<!\d){expected_value}(?!\d)"
    has_expected = bool(re.search(expected_pattern, text))

    correct_steps, wrong_steps = check_equations(text, operands)

    if claims_expected and wrong_claims:
        return (
            "manual_review",
            f"Sprzeczne deklaracje wyniku: {expected_value} oraz "
            f"{wrong_claims}."
        )

    if wrong_claims:
        return (
            "candidate_incorrect",
            f"Zadeklarowany wynik {wrong_claims}, "
            f"oczekiwano {expected_value}."
        )

    if claims_expected or has_expected:
        if wrong_steps:
            return (
                "manual_review",
                "Wykryto oczekiwany wynik, ale też błędne kroki "
                f"pośrednie: {wrong_steps[:3]}."
            )

        if correct_steps:
            return (
                "candidate_correct_with_calculation",
                "Wykryto oczekiwany wynik i poprawne kroki obliczenia: "
                f"{correct_steps[:3]}."
            )

        return (
            "candidate_correct_result_only",
            "Wykryto oczekiwany wynik, ale nie potwierdzono poprawnego "
            "wyprowadzenia obliczenia."
        )

    return (
        "manual_review",
        "Nie udało się wiarygodnie ocenić mnożenia."
    )


# ============================================================
# PERCENTAGE
# ============================================================

PERCENT = r"(\d+(?:\.\d+)?)\s*(?:%|procent\w*|percent)"


def check_percentage(answer, expected):
    """Screen an answer whose expected value is a percentage."""
    text = normalize(answer)

    expected_match = re.search(PERCENT, normalize(expected))

    if not expected_match:
        return "manual_review", "Nieobsługiwany format wartości oczekiwanej."

    expected_value = float(expected_match.group(1))

    found = [float(value) for value in re.findall(PERCENT, text)]

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


# ============================================================
# SYLLOGISM
# ============================================================

def parse_syllogism_expected(expected, language):
    """Return (subject, predicate_word) from e.g. 'Tak, Mruczek jest ssakiem.'"""
    text = normalize(expected)

    if language == "pl":
        match = re.search(
            r"(?:tak|nie)\W*\s*(\w+)\s+(?:nie\s+)?jest\s+(\w+)", text
        )
    else:
        match = re.search(
            r"(?:yes|no)\W*\s*(\w+)\s+is\s+(?:not\s+)?(?:an?\s+)?(\w+)",
            text
        )

    if match:
        return match.group(1), match.group(2)

    # Wartości domyślne z wersji v4.1 (kompatybilność wstecz).
    if language == "pl":
        return "mruczek", "ssakiem"

    return "mruczek", "mammal"


def check_syllogism(answer, language, expected=""):
    """Screen the conclusion of a categorical syllogism."""
    text = normalize(answer)

    if language not in ("pl", "en"):
        return (
            "manual_review",
            f"Nieobsługiwany język: {language}."
        )

    subject, predicate = parse_syllogism_expected(expected, language)
    subject_pattern = fuzzy_word(subject)
    extra_forms = PREDICATE_FORMS.get(predicate, [])

    if language == "pl":
        predicate_pattern = (
            r"(?:jest\s+" + re.escape(predicate)
            + "".join("|" + form for form in extra_forms) + ")"
        )
        negation_pattern = r"\bnie\b|\bnigdy\b"

    else:
        predicate_pattern = (
            r"(?:is\s+(?:not\s+)?(?:an?\s+)?" + re.escape(predicate)
            + r"|isn't\s+(?:an?\s+)?" + re.escape(predicate)
            + "".join("|" + form for form in extra_forms) + ")"
        )
        negation_pattern = r"\bnot\b|\bnever\b|\bisn't\b"

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
            "przypisanie cechy temu samemu obiektowi."
        )

    if has_positive:
        return (
            "candidate_correct_conclusion",
            f"Wykryto stwierdzenie, że '{subject}' -> '{predicate}'. "
            "Poprawność uzasadnienia wymaga osobnej kontroli."
        )

    if has_negative:
        return (
            "candidate_incorrect_conclusion",
            f"Wykryto zaprzeczenie, że '{subject}' -> '{predicate}'."
        )

    return (
        "manual_review",
        "Nie wykryto jednoznacznego przypisania ani zaprzeczenia "
        "cechy w kontekście badanego obiektu."
    )


# ============================================================
# CURRENCY / CPI  (checker tematyczny)
# ============================================================

CURRENCY_PATTERNS = {
    "pl": {
        "correct_conclusion": [
            r"nie oznacza(?: to)? automatycznie",
            r"nie musi oznaczać",
            r"nie powoduje automatycznie",
            r"nie wynika automatycznie",
            r"nie prowadzi automatycznie do",
        ],
        "incorrect_conclusion": [
            r"(?<!nie )automatycznie\s+(?:powoduje|oznacza|prowadzi do)\s+wzrost(?:u)?",
            r"(?<!nie )(?:oznacza|powoduje)\s+automatycznie\s+wzrost(?:u)?",
            r"zawsze powoduje wzrost",
            # v4.1 miało tu "prowadzi[ć]+do" bez spacji - nigdy nie pasowało.
            r"musi\s+prowadzić\s+do\s+wzrost(?:u)?",
        ],
        "correct_direction": [
            r"(?:usd|dolar)[^.!?]{0,100}(?:drożej|więcej\s+złotych|kosztuje\s+więcej\s+pln)",
            r"(?:złoty|pln)[^.!?]{0,100}(?:słabnie|osłabia\s+się|traci\s+na\s+wartości)",
            r"(?:osłabienie|deprecjacja)\s+(?:złotego|pln)",
            r"za\s+(?:jednego\s+)?dolara[^.!?]{0,50}więcej\s+złotych",
        ],
        "incorrect_direction": [
            r"(?:złoty|pln)[^.!?]{0,100}(?:umacnia\s+się|zyskuje\s+na\s+wartości)",
            r"(?:usd|dolar)[^.!?]{0,100}(?:tanieje|kosztuje\s+mniej\s+złotych)",
            r"(?:osłabienie|deprecjacja)\s+(?:dolara|usd)",
            r"(?:złoty|pln)[^.!?]{0,100}(?:jest\s+silniejszy|staje\s+się\s+silniejszy)",
        ],
    },
    "en": {
        "correct_conclusion": [
            r"does not automatically mean",
            r"does not necessarily mean",
            r"does not automatically cause",
            r"does not necessarily cause",
            r"does not automatically lead to",
        ],
        "incorrect_conclusion": [
            r"automatically means an increase",
            r"automatically causes an increase",
            r"always causes an increase",
            r"must lead to an increase",
            r"(?<!not )automatically leads? to an increase",
        ],
        "correct_direction": [
            r"(?:usd|dollar)[^.!?]{0,100}(?:more expensive|costs more|higher in pln)",
            r"(?:pln|zloty|złoty)[^.!?]{0,100}(?:weakens|depreciates|loses value)",
            r"(?:weakening|depreciation)\s+of\s+(?:the\s+)?(?:pln|zloty)",
            r"more\s+zloty[^.!?]{0,50}(?:per|for)\s+(?:one\s+)?dollar",
        ],
        "incorrect_direction": [
            r"(?:pln|zloty|złoty)[^.!?]{0,100}(?:strengthens|appreciates|gains value)",
            r"(?:usd|dollar)[^.!?]{0,100}(?:becomes cheaper|costs less)",
            r"(?:weakening|depreciation)\s+of\s+(?:the\s+)?(?:usd|dollar)",
            r"(?:pln|zloty|złoty)[^.!?]{0,100}(?:becomes stronger|is stronger)",
        ],
    },
}


def check_currency(answer, language):
    """Screen 'does USD/PLN growth automatically mean CPI growth'."""
    text = normalize(answer)

    patterns = CURRENCY_PATTERNS.get(language)

    if patterns is None:
        return (
            "manual_review",
            f"Nieobsługiwany język: {language}."
        )

    def contains_any(group):
        return any(
            re.search(pattern, text)
            for pattern in patterns[group]
        )

    conclusion_correct = contains_any("correct_conclusion")
    conclusion_incorrect = contains_any("incorrect_conclusion")
    direction_correct = contains_any("correct_direction")
    direction_incorrect = contains_any("incorrect_direction")

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


# ============================================================
# DISPATCH
# ============================================================

CHECKERS = {
    "arithmetic_multiplication": lambda r: check_multiplication(
        r.get("answer", ""), r.get("expected", ""), r.get("prompt", "")
    ),
    "percentage_change": lambda r: check_percentage(
        r.get("answer", ""), r.get("expected", "")
    ),
    "logical_syllogism": lambda r: check_syllogism(
        r.get("answer", ""), r.get("language", ""), r.get("expected", "")
    ),
    "currency_vs_inflation": lambda r: check_currency(
        r.get("answer", ""), r.get("language", "")
    ),
}


def apply_truncation_rule(status, evidence, record):
    """Send a positive verdict on a truncated answer to manual review.

    A truncated answer may have been heading for a different conclusion,
    so a "candidate_correct*" verdict cannot stand. A wrong claim that was
    already written before the cut stays wrong, so "candidate_incorrect*"
    and partial errors keep their status with a note.

    Returns (status, evidence, pre_truncation_status).
    """
    if technical_completeness(record)["status"] != "truncated":
        return status, evidence, None

    note = " Odpowiedź ucięta (finish_reason=length)."

    if not status.startswith("candidate_correct"):
        return status, evidence + note, None

    return (
        "manual_review",
        "Odpowiedź ucięta (finish_reason=length) - ocena wstępna "
        f"'{status}' wymaga potwierdzenia. {evidence}",
        status,
    )


def assess_answer(record):
    """Run the checker registered for the record's test_id."""
    test_id = record.get("test_id", "")
    checker = CHECKERS.get(test_id)

    if record.get("status") == "FAIL":
        status = "manual_review"
        evidence = f"Brak odpowiedzi (błąd techniczny): {record.get('error')}"
    elif checker is None:
        status = "manual_review"
        evidence = f"Nieobsługiwany test_id: {test_id}"
    else:
        status, evidence = checker(record)

    status, evidence, pre_status = apply_truncation_rule(
        status, evidence, record
    )

    return {
        "status": status,
        "evidence": evidence,
        "pre_truncation_status": pre_status,
        "is_final_judgement": False,
    }


def detect_repetition(answer):
    """Report sentences repeated verbatim in the answer."""
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
    """Build the analysed copy of one source record."""
    return {
        "model": record.get("model"),
        "test_id": record.get("test_id"),
        "category": record.get("category"),
        "language": record.get("language"),
        "run_index": record.get("run_index"),
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
    """Aggregate screening statuses over all analysed records."""
    counters = defaultdict(Counter)
    manual = Counter()
    records_requiring_human_review = 0
    truncated_records = 0
    by_model_language = defaultdict(Counter)

    dimensions = (
        "answer_screening",
        "technical_completeness",
        "reasoning",
        "consistency",
        "language_quality",
    )

    for record in records:
        assessment = record["automatic_assessment"]
        needs_human_review = False

        for dimension in dimensions:
            status = assessment[dimension]["status"]
            counters[dimension][status] += 1

            if status == "manual_review":
                manual[dimension] += 1
                needs_human_review = True

        if assessment["technical_completeness"]["status"] == "truncated":
            truncated_records += 1

        if needs_human_review:
            records_requiring_human_review += 1

        key = f'{record["model"]} / {record["language"]}'
        by_model_language[key][assessment["answer_screening"]["status"]] += 1

    summary = {"records": len(records)}
    summary.update({d: dict(counters[d]) for d in dimensions})
    summary["human_review"] = {
        "answer_screening_manual_review_required": manual["answer_screening"],
        "reasoning_manual_review_required": manual["reasoning"],
        "consistency_manual_review_required": manual["consistency"],
        "language_quality_manual_review_required": manual["language_quality"],
        "truncated_records": truncated_records,
        "total_records_requiring_human_review": records_requiring_human_review,
    }
    summary["by_model_language"] = {
        key: dict(value)
        for key, value in sorted(by_model_language.items())
    }
    return summary


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=f"{TITLE} - automatic test-result screening"
    )

    parser.add_argument(
        "input",
        nargs="?",
        default="results/test_30_bilingual_quality.json",
        help="Ścieżka do surowego raportu testu JSON."
    )
    parser.add_argument(
        "--output-dir",
        default=str(RESULTS_DIR),
        help="Katalog na raport analizy (domyślnie results/)."
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
        "test": f"{TITLE} - automatic result screening",
        "version": VERSION,
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
            "truncated_answers_require_manual_review": True,
            "reasoning_is_automatically_certified": False,
        },
        "summary": summarize(analyzed),
        "results": analyzed,
    }

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{input_file.stem}_analysis_{VERSION_SUFFIX}.json"

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"=== {TITLE}: AUTOMATIC SCREENING ===")
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
