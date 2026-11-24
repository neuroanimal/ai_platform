"""
Agent-with-RAG tasks: questions about the fictional firm Nordwind.

The facts are in the ``bilingual_qa`` corpus (``rag_benchmark.qa_sets``) and
nowhere else, so a model can only answer from retrieved passages. Three kinds:

- ``lookup``: one fact, copied from one passage;
- ``lookup_calc``: one or two facts plus arithmetic (12 x 49 zl, 41 - 19,
  7:15 to 16:45 in minutes) - where a calculator should help;
- ``general``: general knowledge that needs no documents - where the tools
  should not be needed, and only cost time.

``relevant`` names the corpus documents that hold the facts, so retrieval can
be checked separately from the answer. Polish and English, mixed with the
language of the passage on purpose (cross-lingual retrieval).

``agent_rag`` v1: 11 tasks. The accepted phrases were widened on 2026-11-24
by declined Polish forms (Halinę Wrzos, Warszawę) after the first run; the
questions are unchanged, so earlier reports are re-screened with
``agent_rag_evaluator.rescreen`` instead of being run again.
"""

from dataclasses import dataclass
from typing import List, Sequence

KINDS = ("lookup", "lookup_calc", "general")


@dataclass(frozen=True)
class AgentRagTask:
    """One question with its expected answer and the documents that hold it."""

    task_id: str
    kind: str
    language: str
    question: str
    expected: str
    checker: str
    relevant: Sequence[str]

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"{self.task_id}: kind must be one of {KINDS}")
        if self.kind != "general" and not self.relevant:
            raise ValueError(f"{self.task_id}: a {self.kind} task needs relevant documents")


_T = AgentRagTask
AGENT_RAG_V1: List[AgentRagTask] = [
    _T("lookup_trucks_pl", "lookup", "pl", "Ile ciężarówek elektrycznych ma firma Nordwind?",
       "19", "numeric", ["fleet_en"]),
    _T("lookup_code_en", "lookup", "en", "What is the access code of Nordwind warehouse "
       "number 7?", "4512", "numeric", ["code_pl"]),
    _T("lookup_support_pl", "lookup", "pl", "Do której godziny działa obsługa klienta Nordwind "
       "w dni robocze?", "16:45|16.45", "phrase", ["support_en"]),
    _T("lookup_founder_en", "lookup", "en", "Who founded Nordwind Logistyka?",
       # Polish answers decline the name (seen: "założone przez Halinę Wrzos").
       "Halina Wrzos|Haliny Wrzos|Halinę Wrzos|Halinie Wrzos|Haliną Wrzos", "phrase",
       ["nordwind_pl"]),
    _T("calc_year_en", "lookup_calc", "en", "How much does one year of the Nordwind Express "
       "subscription cost in total, in zloty?", "588", "numeric", ["tariff_pl"]),
    _T("calc_year_pl", "lookup_calc", "pl", "Ile przesyłek maksymalnie obejmuje abonament "
       "Nordwind Express przez 12 miesięcy?", "360", "numeric", ["tariff_pl"]),
    _T("calc_diesel_pl", "lookup_calc", "pl", "Ile ciężarówek firmy Nordwind nie jest "
       "elektrycznych?", "22", "numeric", ["fleet_en"]),
    _T("calc_minutes_en", "lookup_calc", "en", "For how many minutes per working day is "
       "Nordwind customer support available?", "570", "numeric", ["support_en"]),
    _T("calc_years_pl", "lookup_calc", "pl", "Ile lat minęło od założenia firmy Nordwind do "
       "zakończenia projektu Orion?", "14", "numeric", ["nordwind_pl", "orion_en"]),
    _T("general_capital_pl", "general", "pl", "Jakie miasto jest stolicą Polski?",
       "Warszawa|Warszawie|Warszawę|Warszawy|Warsaw", "phrase", []),
    _T("general_mult_en", "general", "en", "What is 12 times 12?", "144", "numeric", []),
]

_REGISTRY = {"agent_rag": AGENT_RAG_V1, "agent_rag@1": AGENT_RAG_V1}


def get_agent_rag_tasks(name: str = "agent_rag") -> List[AgentRagTask]:
    """Task list by name or name@version."""
    if name not in _REGISTRY:
        raise ValueError(f"unknown agent RAG task set {name!r}; available {sorted(_REGISTRY)}")
    return _REGISTRY[name]
