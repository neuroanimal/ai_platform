"""
Built-in benchmark task sets and their registry.

``bilingual_reasoning`` v3 (the default name) adds 12 short tasks to v2;
``bilingual_reasoning@2`` stays available for comparison with earlier runs.

``bilingual_reasoning`` v2 is the task set of
``config/test_env/test_30_bilingual_quality_v2/v3.py`` (v1 differs only in
the "Mrruczek" spelling of the EN syllogism; screening accepts both).
Polish-only runs (the former test_28_quality / test_29) are this set with
``languages=["pl"]``.

Further sets are added with ``register_task_set`` - explicit registration,
no discovery, per doc/arch/DEPENDENCY_RULES.md.
"""

from typing import Dict, List

from ai_platform.backend.domain_layer.business_logic.llm_benchmark.task_model import (
    TaskSet,
    TaskSetError,
    task_from_dict,
)

BILINGUAL_REASONING_V2 = [
    {"id": "arithmetic_multiplication", "category": "mathematics", "checker": "multiplication",
     "languages": {
         "pl": {"prompt": "Ile wynosi 17 razy 23? Podaj wynik i obliczenie.", "expected": "391"},
         "en": {"prompt": "What is 17 times 23? Give the result and show the calculation.",
                "expected": "391"}}},
    {"id": "percentage_change", "category": "mathematics", "checker": "percentage",
     "languages": {
         "pl": {"prompt": "Cena produktu wzrosła ze 100 zł do 112 zł. O ile procent wzrosła?",
                "expected": "12%"},
         "en": {"prompt": ("The price of a product increased from 100 PLN to 112 PLN. "
                           "By what percentage did it increase?"), "expected": "12%"}}},
    {"id": "logical_syllogism", "category": "logic", "checker": "syllogism",
     "languages": {
         "pl": {"prompt": ("Wszystkie koty są ssakami. Mruczek jest kotem. "
                           "Czy Mruczek jest ssakiem? Uzasadnij."),
                "expected": "Tak, Mruczek jest ssakiem."},
         "en": {"prompt": ("All cats are mammals. Mruczek is a cat. "
                           "Is Mruczek a mammal? Explain your answer."),
                "expected": "Yes, Mruczek is a mammal."}}},
    {"id": "currency_vs_inflation", "category": "economics", "checker": "currency_vs_cpi",
     "languages": {
         "pl": {"prompt": ("Czy wzrost kursu USD/PLN oznacza automatycznie wzrost inflacji "
                           "CPI w Polsce? Wyjaśnij krótko."),
                "expected": ("Nie. Kurs walutowy może wpływać na ceny importu i CPI, ale "
                             "wzrost kursu nie oznacza automatycznie wzrostu CPI.")},
         "en": {"prompt": ("Does an increase in the USD/PLN exchange rate automatically mean "
                           "an increase in CPI inflation in Poland? Explain briefly."),
                "expected": ("No. The exchange rate can affect import prices and CPI, but an "
                             "increase in the exchange rate does not automatically mean an "
                             "increase in CPI.")}}},
]

def _task(task_id, category, checker, pl, en):
    """Compact task definition: pl/en are (prompt, expected) pairs."""
    return {"id": task_id, "category": category, "checker": checker,
            "languages": {"pl": {"prompt": pl[0], "expected": pl[1]},
                          "en": {"prompt": en[0], "expected": en[1]}}}


# v3 = v2 plus 12 short tasks with one checkable answer each. Expected values
# for "phrase" list accepted spellings separated by "|".
BILINGUAL_REASONING_V3 = BILINGUAL_REASONING_V2 + [
    _task("word_problem", "mathematics", "numeric",
          ("Jabłko kosztuje 3 zł, a gruszka 5 zł. Ile zapłacisz za 4 jabłka i 2 gruszki?", "22"),
          ("An apple costs 3 PLN and a pear 5 PLN. How much do 4 apples and 2 pears cost?",
           "22")),
    _task("division_remainder", "mathematics", "numeric",
          ("Jaka jest reszta z dzielenia 100 przez 7?", "2"),
          ("What is the remainder when 100 is divided by 7?", "2")),
    _task("percentage_of", "mathematics", "numeric",
          ("Ile to jest 15% z 200?", "30"), ("What is 15% of 200?", "30")),
    _task("unit_conversion", "mathematics", "numeric",
          ("Ile metrów ma 2,5 kilometra?", "2500"), ("How many metres are 2.5 kilometres?",
                                                      "2500")),
    _task("number_sequence", "logic", "numeric",
          ("Jaka liczba jest następna w ciągu: 2, 4, 8, 16?", "32"),
          ("What is the next number in the sequence 2, 4, 8, 16?", "32")),
    _task("letter_count", "language", "numeric",
          ("Ile razy litera a występuje w słowie banan?", "2"),
          ("How many times does the letter a occur in the word banana?", "3")),
    _task("time_arithmetic", "mathematics", "phrase",
          ("Pociąg odjeżdża o 14:45 i jedzie 2 godziny 30 minut. O której godzinie przyjedzie?",
           "17:15|17.15"),
          ("A train leaves at 14:45 and travels for 2 hours 30 minutes. When does it arrive?",
           "17:15|17.15|5:15 pm|5:15 p.m.")),
    _task("negated_syllogism", "logic", "yes_no",
          ("Żaden ptak nie jest ssakiem. Wróbel jest ptakiem. Czy wróbel jest ssakiem?", "Nie"),
          ("No bird is a mammal. A sparrow is a bird. Is a sparrow a mammal?", "No")),
    _task("decimal_comparison", "mathematics", "yes_no",
          ("Czy liczba 0,7 jest większa od liczby 0,65?", "Tak"),
          ("Is the number 0.7 greater than 0.65?", "Yes")),
    _task("capital_city", "knowledge", "phrase",
          ("Jaka jest stolica Australii?", "Canberra|Canberze|Canberry"),
          ("What is the capital of Australia?", "Canberra")),
    _task("weekday", "knowledge", "phrase",
          ("Jaki dzień tygodnia był 1 stycznia 2000 roku?", "sobota|sobotę|soboty"),
          ("What day of the week was 1 January 2000?", "Saturday")),
    _task("plural_form", "language", "phrase",
          ("Podaj liczbę mnogą rzeczownika 'pies'.", "psy"),
          ("What is the plural of the noun 'mouse'?", "mice")),
]

_REGISTRY: Dict[str, TaskSet] = {}


def register_task_set(task_set: TaskSet) -> None:
    """Register a task set under ``name`` (and ``name@version``)."""
    for key in (task_set.name, f"{task_set.name}@{task_set.version}"):
        if key in _REGISTRY and _REGISTRY[key] is not task_set:
            raise TaskSetError(f"task set {key!r} already registered")
        _REGISTRY[key] = task_set


def get_task_set(name: str) -> TaskSet:
    """Task set by ``name`` or ``name@version``."""
    if name not in _REGISTRY:
        raise TaskSetError(f"unknown task set {name!r}; available: {list_task_sets()}")
    return _REGISTRY[name]


def list_task_sets() -> List[str]:
    """Registered names (with versions)."""
    return sorted(_REGISTRY)


register_task_set(TaskSet(
    name="bilingual_reasoning", version="2",
    description="Arithmetic, percentage, syllogism and economics questions in Polish and English.",
    tasks=[task_from_dict(t) for t in BILINGUAL_REASONING_V2]))

# "bilingual_reasoning" resolves to the newest version; reports name the version.
_REGISTRY.pop("bilingual_reasoning")
register_task_set(TaskSet(
    name="bilingual_reasoning", version="3",
    description=("v2 plus 12 short tasks: word problems, remainder, percentages, units, "
                 "sequences, letter counting, time, negation, decimals, facts, plurals."),
    tasks=[task_from_dict(t) for t in BILINGUAL_REASONING_V3]))
