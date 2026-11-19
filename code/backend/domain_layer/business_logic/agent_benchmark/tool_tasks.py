"""
Tool-use tasks for the agent benchmark.

Each task names the tools a good agent uses (``expected_tools``; empty =
answer without tools) and the expected answer with its screening checker.
The tasks are built so that guessing does not work: products of large
numbers, conversions with exact results, and facts about the fictional firm
Nordwind (``bilingual_qa`` corpus) that only the search tool can supply.

``tool_use`` v1: 9 tasks, Polish and English.
"""

from dataclasses import dataclass
from typing import List, Sequence


@dataclass(frozen=True)
class ToolTask:
    """One question for the agent."""

    task_id: str
    language: str
    question: str
    expected: str
    checker: str
    expected_tools: Sequence[str]


TOOL_USE_V1: List[ToolTask] = [
    ToolTask("calc_pl", "pl", "Ile wynosi 17 razy 23 razy 19?", "7429", "numeric",
             ["calculator"]),
    ToolTask("calc_big_en", "en", "What is 123456 multiplied by 789?", "97406784", "numeric",
             ["calculator"]),
    ToolTask("calc_expr_en", "en", "Compute (48.5 - 12.25) / 0.25.", "145", "numeric",
             ["calculator"]),
    ToolTask("convert_pl", "pl", "Ile minut ma 2,5 dnia?", "3600", "numeric",
             ["convert_units|calculator"]),
    ToolTask("convert_en", "en", "Convert 77 degrees Fahrenheit to Celsius.", "25", "numeric",
             ["convert_units|calculator"]),
    ToolTask("search_pl", "pl", "Ile ciężarówek elektrycznych ma firma Nordwind?", "19",
             "numeric", ["search_documents"]),
    ToolTask("search_en", "en", "What is the access code of Nordwind warehouse number 7?",
             "4512", "numeric", ["search_documents"]),
    ToolTask("search_calc_en", "en", "How much does one year of the Nordwind Express "
             "subscription cost in total?", "588", "numeric",
             ["search_documents", "calculator"]),
    ToolTask("no_tool_pl", "pl", "Jakie miasto jest stolicą Polski?", "Warszawa|Warszawie|"
             "Warsaw", "phrase", []),
]

_REGISTRY = {"tool_use": TOOL_USE_V1, "tool_use@1": TOOL_USE_V1}


def get_tool_tasks(name: str = "tool_use") -> List[ToolTask]:
    """Task list by name or name@version."""
    if name not in _REGISTRY:
        raise ValueError(f"unknown tool task set {name!r}; available {sorted(_REGISTRY)}")
    return _REGISTRY[name]
