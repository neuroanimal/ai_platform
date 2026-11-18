#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TEST 30A v4.2 — SELFTEST

Testy kontrolne heurystyk bez:
- zapytań do modeli,
- odczytu raportów benchmarkowych,
- modyfikacji raportów źródłowych.

Zawiera wszystkie przypadki z selftestu v4.1 (mnożenie z promptem,
bo v4.2 odczytuje operandy z promptu) oraz przypadki regresyjne
dla poprawek v4.2:
- słowna deklaracja błędnego wyniku ("equals 85") - realna odpowiedź
  qwen25-05b-localai [EN] z raportu test_30;
- "musi prowadzić do wzrostu" (naprawiony regex);
- odpowiedź ucięta (finish_reason=length) -> manual_review;
- inne operandy i inny podmiot sylogizmu (brak twardego kodowania);
- pisownia Mruczek / Mrruczek;
- spójność numeru wersji.

Uruchomienie:
    python test_30a_analysis_v4_2_selftest.py
"""

import importlib.util
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SOURCE_FILE = BASE_DIR / "test_30a_analysis_v4_2.py"

spec = importlib.util.spec_from_file_location(
    "test_30a_analysis_v4_2",
    SOURCE_FILE
)

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


tests = []

PROMPT_PL = "Ile wynosi 17 razy 23? Podaj wynik i obliczenie."
PROMPT_EN = "What is 17 times 23? Give the result and show the calculation."


def add_test(name, function, expected_status):
    """Register one selftest case."""
    tests.append((name, function, expected_status))


def assess(**record):
    """Run assess_answer and return (status, evidence) like a checker."""
    result = module.assess_answer(record)
    return result["status"], result["evidence"]


# ============================================================
# MULTIPLICATION (v4.1 cases)
# ============================================================

add_test(
    "multiplication_correct",
    lambda: module.check_multiplication(
        "17 * 23 = 391", "391", PROMPT_PL
    ),
    "candidate_correct_result_only"
)

add_test(
    "multiplication_detailed",
    lambda: module.check_multiplication(
        "17 * 20 = 340. 17 * 3 = 51. 340 + 51 = 391.", "391", PROMPT_PL
    ),
    "candidate_correct_with_calculation"
)

add_test(
    "multiplication_incorrect",
    lambda: module.check_multiplication(
        "17 * 23 = 392", "391", PROMPT_PL
    ),
    "candidate_incorrect"
)

add_test(
    "multiplication_missing_result",
    lambda: module.check_multiplication(
        "17 times 23", "391", PROMPT_EN
    ),
    "manual_review"
)

# ============================================================
# MULTIPLICATION (v4.2 regressions)
# ============================================================

QWEN05_EN_TAIL = (
    "4. Add the two results together:\n"
    "   17 × 3 = 51\n"
    "   17 × 2 = 34\n"
    "   51 + 34 = 85\n\n"
    "So, 17 times 23 equals 85."
)

add_test(
    "multiplication_equals_85_real_answer",
    lambda: module.check_multiplication(QWEN05_EN_TAIL, "391", PROMPT_EN),
    "candidate_incorrect"
)

add_test(
    "multiplication_equals_85_short",
    lambda: module.check_multiplication(
        "17 times 23 equals 85.", "391", PROMPT_EN
    ),
    "candidate_incorrect"
)

add_test(
    "multiplication_wynosi_wrong_pl",
    lambda: module.check_multiplication(
        "17 razy 23 wynosi 381.", "391", PROMPT_PL
    ),
    "candidate_incorrect"
)

add_test(
    "multiplication_contradictory_claims",
    lambda: module.check_multiplication(
        "17 × 23 = 391. Ostatecznie 17 razy 23 wynosi 381.", "391", PROMPT_PL
    ),
    "manual_review"
)

add_test(
    "multiplication_markdown_bold",
    lambda: module.check_multiplication(
        "17 × 23 = **391**", "391", PROMPT_PL
    ),
    "candidate_correct_result_only"
)

add_test(
    "multiplication_result_label_not_a_claim",
    lambda: module.check_multiplication(
        "Wynik: 17 * 23 = 391", "391", PROMPT_PL
    ),
    "candidate_correct_result_only"
)

add_test(
    "multiplication_wrong_intermediate_step",
    lambda: module.check_multiplication(
        "17 * 20 = 340. 17 * 3 = 52. 17 × 23 = 391.", "391", PROMPT_PL
    ),
    "manual_review"
)

add_test(
    "multiplication_other_operands",
    lambda: module.check_multiplication(
        "12 * 10 = 120. 12 * 3 = 36. 120 + 36 = 156.",
        "156",
        "Ile wynosi 12 razy 13?"
    ),
    "candidate_correct_with_calculation"
)

add_test(
    "multiplication_inconsistent_expected",
    lambda: module.check_multiplication(
        "17 * 23 = 391", "390", PROMPT_PL
    ),
    "manual_review"
)


# ============================================================
# PERCENTAGE
# ============================================================

add_test(
    "percentage_correct_pl",
    lambda: module.check_percentage("Wzrost wynosi 12%.", "12%"),
    "candidate_correct"
)

add_test(
    "percentage_incorrect",
    lambda: module.check_percentage("Wzrost wynosi 2%.", "12%"),
    "candidate_incorrect"
)

add_test(
    "percentage_contradictory",
    lambda: module.check_percentage(
        "Wzrost wynosi 12%, ale wcześniej obliczyłem 2%.", "12%"
    ),
    "manual_review"
)

add_test(
    "percentage_word_procent",
    lambda: module.check_percentage("Cena wzrosła o 12 procent.", "12%"),
    "candidate_correct"
)


# ============================================================
# SYLLOGISM
# ============================================================

add_test(
    "syllogism_correct_pl",
    lambda: module.check_syllogism("Tak, Mruczek jest ssakiem.", "pl"),
    "candidate_correct_conclusion"
)

add_test(
    "syllogism_incorrect_pl",
    lambda: module.check_syllogism("Mruczek nie jest ssakiem.", "pl"),
    "candidate_incorrect_conclusion"
)

add_test(
    "syllogism_contradictory_pl",
    lambda: module.check_syllogism(
        "Mruczek jest ssakiem, ale Mruczek nie jest ssakiem.", "pl"
    ),
    "manual_review"
)

add_test(
    "syllogism_ambiguous_pl",
    lambda: module.check_syllogism("Tak, to prawda.", "pl"),
    "manual_review"
)

add_test(
    "syllogism_correct_en",
    lambda: module.check_syllogism("Yes, Mrruczek is a mammal.", "en"),
    "candidate_correct_conclusion"
)

add_test(
    "syllogism_incorrect_en",
    lambda: module.check_syllogism("Mrruczek is not a mammal.", "en"),
    "candidate_incorrect_conclusion"
)

add_test(
    "syllogism_unrelated_negation_pl",
    lambda: module.check_syllogism(
        "Nie mam wątpliwości, że Mruczek jest ssakiem.", "pl"
    ),
    "candidate_correct_conclusion"
)

add_test(
    "syllogism_spelling_mruczek_vs_mrruczek_en",
    lambda: module.check_syllogism(
        "Yes, Mruczek is a mammal.", "en", "Yes, Mrruczek is a mammal."
    ),
    "candidate_correct_conclusion"
)

add_test(
    "syllogism_other_subject_pl",
    lambda: module.check_syllogism(
        "Tak, Burek jest ssakiem, bo każdy pies jest ssakiem.",
        "pl",
        "Tak, Burek jest ssakiem."
    ),
    "candidate_correct_conclusion"
)

add_test(
    "syllogism_other_subject_ignores_default_pl",
    lambda: module.check_syllogism(
        "Mruczek jest ssakiem.", "pl", "Tak, Burek jest ssakiem."
    ),
    "manual_review"
)

add_test(
    "syllogism_belongs_to_mammals_pl",
    lambda: module.check_syllogism(
        "Mruczek należy do ssaków.", "pl", "Tak, Mruczek jest ssakiem."
    ),
    "candidate_correct_conclusion"
)


# ============================================================
# CURRENCY / CPI
# ============================================================

add_test(
    "currency_correct_pl",
    lambda: module.check_currency(
        "Wzrost USD/PLN oznacza, że dolar kosztuje więcej złotych, "
        "a złoty osłabia się. Nie oznacza to automatycznie wzrostu CPI.",
        "pl"
    ),
    "candidate_correct_conclusion"
)

add_test(
    "currency_wrong_direction_pl",
    lambda: module.check_currency(
        "Wzrost USD/PLN oznacza, że złoty umacnia się. "
        "Nie oznacza to automatycznie wzrostu CPI.",
        "pl"
    ),
    "candidate_partial_direction_error"
)

add_test(
    "currency_missing_direction_pl",
    lambda: module.check_currency(
        "Wzrost kursu nie oznacza automatycznie wzrostu CPI.", "pl"
    ),
    "candidate_correct_conclusion_direction_not_assessed"
)

add_test(
    "currency_wrong_conclusion_pl",
    lambda: module.check_currency(
        "Wzrost USD/PLN automatycznie powoduje wzrost CPI.", "pl"
    ),
    "candidate_incorrect_conclusion"
)

add_test(
    "currency_correct_en",
    lambda: module.check_currency(
        "A higher USD/PLN rate means the dollar costs more PLN "
        "and the zloty weakens. It does not automatically mean "
        "an increase in CPI.",
        "en"
    ),
    "candidate_correct_conclusion"
)

add_test(
    "currency_wrong_direction_en",
    lambda: module.check_currency(
        "A higher USD/PLN rate means the zloty strengthens. "
        "It does not automatically mean an increase in CPI.",
        "en"
    ),
    "candidate_partial_direction_error"
)

add_test(
    "currency_contradictory_conclusion_pl",
    lambda: module.check_currency(
        "Zmiana kursu nie oznacza automatycznie wzrostu CPI, "
        "ale automatycznie powoduje wzrost CPI.",
        "pl"
    ),
    "manual_review"
)

add_test(
    "currency_contradictory_direction_pl",
    lambda: module.check_currency(
        "Wzrost USD/PLN oznacza, że złoty słabnie, "
        "ale jednocześnie złoty umacnia się.",
        "pl"
    ),
    "manual_review"
)

add_test(
    "currency_alternative_direction_pl",
    lambda: module.check_currency(
        "Wzrost USD/PLN oznacza, że za jednego dolara "
        "trzeba zapłacić więcej złotych. "
        "Nie oznacza to automatycznie wzrostu CPI.",
        "pl"
    ),
    "candidate_correct_conclusion"
)

add_test(
    "currency_musi_prowadzic_do_pl",
    lambda: module.check_currency(
        "Wzrost USD/PLN musi prowadzić do wzrostu CPI.", "pl"
    ),
    "candidate_incorrect_conclusion"
)

add_test(
    "currency_musi_prowadzic_do_vs_nie_oznacza_pl",
    lambda: module.check_currency(
        "Nie oznacza to automatycznie wzrostu CPI, choć słabszy złoty "
        "musi prowadzić do wzrostu cen importu.",
        "pl"
    ),
    "manual_review"
)


# ============================================================
# assess_answer: truncation, technical failure, unknown test_id
# ============================================================

add_test(
    "truncated_correct_goes_to_manual_review",
    lambda: assess(
        test_id="arithmetic_multiplication", language="pl",
        prompt=PROMPT_PL, expected="391", answer="17 * 23 = 391",
        finish_reason="length",
    ),
    "manual_review"
)

add_test(
    "truncated_keeps_pre_status",
    lambda: (
        module.assess_answer({
            "test_id": "arithmetic_multiplication", "language": "pl",
            "prompt": PROMPT_PL, "expected": "391",
            "answer": "17 * 23 = 391", "finish_reason": "length",
        })["pre_truncation_status"],
        "",
    ),
    "candidate_correct_result_only"
)

add_test(
    "not_truncated_correct_stays",
    lambda: assess(
        test_id="arithmetic_multiplication", language="pl",
        prompt=PROMPT_PL, expected="391", answer="17 * 23 = 391",
        finish_reason="stop",
    ),
    "candidate_correct_result_only"
)

add_test(
    "truncated_incorrect_stays_incorrect",
    lambda: assess(
        test_id="currency_vs_inflation", language="pl",
        expected="Nie.", finish_reason="length",
        answer=(
            "Nie, wzrost kursu USD/PLN oznacza automatycznie wzrost "
            "inflacji CPI w Polsce. Wzrost kur"
        ),
    ),
    "candidate_incorrect_conclusion"
)

add_test(
    "technical_fail_record",
    lambda: assess(
        test_id="arithmetic_multiplication", language="pl",
        status="FAIL", error="timeout",
    ),
    "manual_review"
)

add_test(
    "unknown_test_id",
    lambda: assess(test_id="something_new", language="pl", answer="x"),
    "manual_review"
)


# ============================================================
# VERSION CONSISTENCY
# ============================================================

add_test(
    "version_consistency",
    lambda: (
        "ok" if (
            module.VERSION == "4.2"
            and module.VERSION_SUFFIX == "v4_2"
            and f"v{module.VERSION}" in module.__doc__
            and module.TITLE == "TEST 30A v4.2"
        ) else "mismatch",
        "",
    ),
    "ok"
)


# ============================================================
# EXECUTION
# ============================================================

def main():
    """Run all registered cases and exit non-zero on any failure."""
    print(f"=== {module.TITLE} SELFTEST ===\n")

    passed = 0
    failed = 0

    for name, function, expected_status in tests:
        try:
            result = function()
            actual_status = result[0]

            if actual_status == expected_status:
                passed += 1
                print(f"PASS: {name}")
            else:
                failed += 1
                print(f"FAIL: {name}")
                print(f"  expected: {expected_status}")
                print(f"  actual:   {actual_status}")
                print(f"  evidence: {result[1]}")

        except Exception as exc:  # pylint: disable=broad-exception-caught
            failed += 1
            print(f"ERROR: {name}")
            print(f"  {type(exc).__name__}: {exc}")

    print("\n" + "=" * 55)
    print(f"TOTAL: {len(tests)}")
    print(f"PASS:  {passed}")
    print(f"FAIL:  {failed}")
    print("=" * 55)

    if failed:
        raise SystemExit(1)

    print("\nAll self-tests passed.")


if __name__ == "__main__":
    main()
