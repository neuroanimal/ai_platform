
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TEST 30A v4.1 — SELFTEST

Testy kontrolne heurystyk bez:
- zapytań do modeli,
- odczytu raportów benchmarkowych,
- modyfikacji raportów źródłowych.

Uruchomienie:
    python test_30a_analysis_v4_1_selftest.py
"""

import importlib.util
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SOURCE_FILE = BASE_DIR / "test_30a_analysis_v4_1.py"

spec = importlib.util.spec_from_file_location(
    "test_30a_analysis_v4_1",
    SOURCE_FILE
)

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


tests = []


def add_test(name, function, expected_status):
    tests.append((name, function, expected_status))


# ============================================================
# MULTIPLICATION
# ============================================================

add_test(
    "multiplication_correct",
    lambda: module.check_multiplication(
        "17 * 23 = 391",
        "391"
    ),
    "candidate_correct_result_only"
)

add_test(
    "multiplication_detailed",
    lambda: module.check_multiplication(
        "17 * 20 = 340. 17 * 3 = 51. 340 + 51 = 391.",
        "391"
    ),
    "candidate_correct_with_calculation"
)

add_test(
    "multiplication_incorrect",
    lambda: module.check_multiplication(
        "17 * 23 = 392",
        "391"
    ),
    "candidate_incorrect"
)

add_test(
    "multiplication_missing_result",
    lambda: module.check_multiplication(
        "17 times 23",
        "391"
    ),
    "manual_review"
)


# ============================================================
# PERCENTAGE
# ============================================================

add_test(
    "percentage_correct_pl",
    lambda: module.check_percentage(
        "Wzrost wynosi 12%.",
        "12%"
    ),
    "candidate_correct"
)

add_test(
    "percentage_incorrect",
    lambda: module.check_percentage(
        "Wzrost wynosi 2%.",
        "12%"
    ),
    "candidate_incorrect"
)

add_test(
    "percentage_contradictory",
    lambda: module.check_percentage(
        "Wzrost wynosi 12%, ale wcześniej obliczyłem 2%.",
        "12%"
    ),
    "manual_review"
)


# ============================================================
# SYLLOGISM
# ============================================================

add_test(
    "syllogism_correct_pl",
    lambda: module.check_syllogism(
        "Tak, Mruczek jest ssakiem.",
        "pl"
    ),
    "candidate_correct_conclusion"
)

add_test(
    "syllogism_incorrect_pl",
    lambda: module.check_syllogism(
        "Mruczek nie jest ssakiem.",
        "pl"
    ),
    "candidate_incorrect_conclusion"
)

add_test(
    "syllogism_contradictory_pl",
    lambda: module.check_syllogism(
        "Mruczek jest ssakiem, ale Mruczek nie jest ssakiem.",
        "pl"
    ),
    "manual_review"
)

add_test(
    "syllogism_ambiguous_pl",
    lambda: module.check_syllogism(
        "Tak, to prawda.",
        "pl"
    ),
    "manual_review"
)

add_test(
    "syllogism_correct_en",
    lambda: module.check_syllogism(
        "Yes, Mrruczek is a mammal.",
        "en"
    ),
    "candidate_correct_conclusion"
)

add_test(
    "syllogism_incorrect_en",
    lambda: module.check_syllogism(
        "Mrruczek is not a mammal.",
        "en"
    ),
    "candidate_incorrect_conclusion"
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
        "Wzrost kursu nie oznacza automatycznie wzrostu CPI.",
        "pl"
    ),
    "candidate_correct_conclusion_direction_not_assessed"
)

add_test(
    "currency_wrong_conclusion_pl",
    lambda: module.check_currency(
        "Wzrost USD/PLN automatycznie powoduje wzrost CPI.",
        "pl"
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
    "syllogism_unrelated_negation_pl",
    lambda: module.check_syllogism(
        "Nie mam wątpliwości, że Mruczek jest ssakiem.",
        "pl"
    ),
    "candidate_correct_conclusion"
)

# ============================================================
# EXECUTION
# ============================================================

print("=== TEST 30A v4.1 SELFTEST ===\n")

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

    except Exception as exc:
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


