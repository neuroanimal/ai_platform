"""Unit tests of the integrated answer screening.

Ported from config/test_env/test_30a_analysis_v4_2_selftest.py: the same
46 cases (plus 4.3 regressions taken from real answers) (v4.1 cases, v4.2 regressions incl. the real qwen 0.5B "equals 85"
answer, truncation and technical-failure handling), now as pytest cases
against ``ai_platform.common.evaluation.answer_screening``.
"""

import pytest

from ai_platform.common.evaluation import answer_screening as s

PL = "Ile wynosi 17 razy 23? Podaj wynik i obliczenie."
EN = "What is 17 times 23? Give the result and show the calculation."
QWEN05_EN_TAIL = ("4. Add the two results together:\n   17 × 3 = 51\n   17 × 2 = 34\n"
                  "   51 + 34 = 85\n\nSo, 17 times 23 equals 85.")

MULTIPLICATION = [
    ("17 * 23 = 391", "391", PL, "candidate_correct_result_only"),
    ("17 * 20 = 340. 17 * 3 = 51. 340 + 51 = 391.", "391", PL, "candidate_correct_with_calculation"),
    ("17 * 23 = 392", "391", PL, "candidate_incorrect"),
    ("17 times 23", "391", EN, "manual_review"),
    (QWEN05_EN_TAIL, "391", EN, "candidate_incorrect"),
    ("17 times 23 equals 85.", "391", EN, "candidate_incorrect"),
    ("17 razy 23 wynosi 381.", "391", PL, "candidate_incorrect"),
    ("17 × 23 = 391. Ostatecznie 17 razy 23 wynosi 381.", "391", PL, "manual_review"),
    ("17 × 23 = **391**", "391", PL, "candidate_correct_result_only"),
    ("Wynik: 17 * 23 = 391", "391", PL, "candidate_correct_result_only"),
    ("17 * 20 = 340. 17 * 3 = 52. 17 × 23 = 391.", "391", PL, "manual_review"),
    ("12 * 10 = 120. 12 * 3 = 36. 120 + 36 = 156.", "156", "Ile wynosi 12 razy 13?",
     "candidate_correct_with_calculation"),
    ("17 * 23 = 391", "390", PL, "manual_review"),
    # 4.3 regression: real qwen2.5:1.5b answer, a term of a chain is not a step
    ("17 × 23 = (10 + 7) × (20 + 3) = 10 × 20 + 10 × 3 + 7 × 20 + 7 × 3 = 200 + 30 + 140 + 21 "
     "= 340 + 51 = 391 So, 17 times 23 equals 391.", "391", EN,
     "candidate_correct_with_calculation"),
    # 4.4 regressions: LaTeX markup, and a chained right-hand side is no result claim
    (r"\[ 17 \times 23 = 17 \times (20 + 3) = 340 + 51 = 391 \]", "391", PL,
     "candidate_correct_with_calculation"),
    (r"17 \times 23 = \boxed{391}", "391", PL, "candidate_correct_result_only"),
]

PERCENTAGE = [
    ("Wzrost wynosi 12%.", "candidate_correct"),
    ("Wzrost wynosi 2%.", "candidate_incorrect"),
    ("Wzrost wynosi 12%, ale wcześniej obliczyłem 2%.", "manual_review"),
    ("Cena wzrosła o 12 procent.", "candidate_correct"),
    # 4.3 regression: real qwen2.5:3b answer, "* 100%" is a factor
    ("(12 zł / 100 zł) * 100% = 12% Zatem cena wzrosła o 12%.", "candidate_correct"),
    ("Wzrost o 12%, a cena to 100% ceny bazowej plus 12%.", "manual_review"),
    (r"\left( \frac{12}{100} \right) \times 100\% = 12\%", "candidate_correct"),
]

SYLLOGISM = [
    ("Tak, Mruczek jest ssakiem.", "pl", "", "candidate_correct_conclusion"),
    ("Mruczek nie jest ssakiem.", "pl", "", "candidate_incorrect_conclusion"),
    ("Mruczek jest ssakiem, ale Mruczek nie jest ssakiem.", "pl", "", "manual_review"),
    ("Tak, to prawda.", "pl", "", "manual_review"),
    ("Yes, Mrruczek is a mammal.", "en", "", "candidate_correct_conclusion"),
    ("Mrruczek is not a mammal.", "en", "", "candidate_incorrect_conclusion"),
    ("Nie mam wątpliwości, że Mruczek jest ssakiem.", "pl", "", "candidate_correct_conclusion"),
    ("Yes, Mruczek is a mammal.", "en", "Yes, Mrruczek is a mammal.",
     "candidate_correct_conclusion"),
    ("Tak, Burek jest ssakiem, bo każdy pies jest ssakiem.", "pl", "Tak, Burek jest ssakiem.",
     "candidate_correct_conclusion"),
    ("Mruczek jest ssakiem.", "pl", "Tak, Burek jest ssakiem.", "manual_review"),
    ("Mruczek należy do ssaków.", "pl", "Tak, Mruczek jest ssakiem.",
     "candidate_correct_conclusion"),
]

CURRENCY = [
    ("Wzrost USD/PLN oznacza, że dolar kosztuje więcej złotych, a złoty osłabia się. "
     "Nie oznacza to automatycznie wzrostu CPI.", "pl", "candidate_correct_conclusion"),
    ("Wzrost USD/PLN oznacza, że złoty umacnia się. Nie oznacza to automatycznie wzrostu CPI.",
     "pl", "candidate_partial_direction_error"),
    ("Wzrost kursu nie oznacza automatycznie wzrostu CPI.", "pl",
     "candidate_correct_conclusion_direction_not_assessed"),
    ("Wzrost USD/PLN automatycznie powoduje wzrost CPI.", "pl", "candidate_incorrect_conclusion"),
    ("A higher USD/PLN rate means the dollar costs more PLN and the zloty weakens. It does "
     "not automatically mean an increase in CPI.", "en", "candidate_correct_conclusion"),
    ("A higher USD/PLN rate means the zloty strengthens. It does not automatically mean an "
     "increase in CPI.", "en", "candidate_partial_direction_error"),
    ("Zmiana kursu nie oznacza automatycznie wzrostu CPI, ale automatycznie powoduje wzrost CPI.",
     "pl", "manual_review"),
    ("Wzrost USD/PLN oznacza, że złoty słabnie, ale jednocześnie złoty umacnia się.", "pl",
     "manual_review"),
    ("Wzrost USD/PLN oznacza, że za jednego dolara trzeba zapłacić więcej złotych. "
     "Nie oznacza to automatycznie wzrostu CPI.", "pl", "candidate_correct_conclusion"),
    ("Wzrost USD/PLN musi prowadzić do wzrostu CPI.", "pl", "candidate_incorrect_conclusion"),
    ("Nie oznacza to automatycznie wzrostu CPI, choć słabszy złoty musi prowadzić do wzrostu "
     "cen importu.", "pl", "manual_review"),
]


@pytest.mark.parametrize("answer,expected,prompt,status", MULTIPLICATION)
def test_multiplication(answer, expected, prompt, status):
    assert s.check_multiplication(answer, expected, prompt)[0] == status


@pytest.mark.parametrize("answer,status", PERCENTAGE)
def test_percentage(answer, status):
    assert s.check_percentage(answer, "12%")[0] == status


@pytest.mark.parametrize("answer,language,expected,status", SYLLOGISM)
def test_syllogism(answer, language, expected, status):
    assert s.check_syllogism(answer, language, expected)[0] == status


@pytest.mark.parametrize("answer,language,status", CURRENCY)
def test_currency(answer, language, status):
    assert s.check_currency(answer, language)[0] == status


def record(**fields):
    """Benchmark record with defaults."""
    return {"test_id": "arithmetic_multiplication", "language": "pl", "prompt": PL,
            "expected": "391", "answer": "17 * 23 = 391", "finish_reason": "stop", **fields}


def test_truncated_positive_goes_to_manual_review_with_pre_status():
    result = s.assess_answer(record(finish_reason="length"))
    assert result["status"] == "manual_review"
    assert result["pre_truncation_status"] == "candidate_correct_result_only"


def test_truncated_wrong_claim_stays_wrong():
    result = s.assess_answer(record(
        test_id="currency_vs_inflation", finish_reason="length",
        answer="Nie, wzrost kursu USD/PLN oznacza automatycznie wzrost inflacji CPI. Wzrost kur"))
    assert result["status"] == "candidate_incorrect_conclusion"


def test_not_truncated_and_explicit_checker():
    assert s.assess_answer(record())["status"] == "candidate_correct_result_only"
    assert s.assess_answer(record(test_id="renamed", checker="multiplication"))["checker"] \
        == "multiplication"


def test_technical_failure_and_unknown_checker():
    assert s.assess_answer(record(status="FAIL", error="timeout"))["status"] == "manual_review"
    assert s.assess_answer(record(test_id="new", answer="x"))["status"] == "manual_review"


def test_register_checker_is_explicit():
    with pytest.raises(ValueError):
        s.register_checker("multiplication", lambda r: ("manual_review", ""))


def test_screen_report_summary():
    report = {"results": [record(), record(finish_reason="length"),
                          record(model="m2", answer="17 * 23 = 392")]}
    for row in report["results"]:
        row.setdefault("model", "m1")
    analysis = s.screen_report(report)
    assert analysis["summary"]["records"] == 3
    assert analysis["summary"]["truncated_records"] == 1
    assert analysis["summary"]["by_model_language"]["m2 / pl"] == {"candidate_incorrect": 1}
    assert all(r["automatic_assessment"]["answer_screening"]["is_final_judgement"] is False
               for r in analysis["results"])
    with pytest.raises(ValueError):
        s.screen_report({})
