"""
Built-in benchmark task sets and their registry.

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
