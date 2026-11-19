"""
Task set lookup for callers above the service layer.

The UI layer may not import the domain layer directly
(doc/arch/DEPENDENCY_RULES.md: ui_layer -> service_layer -> domain_layer),
so this service is the CLI's access to the registered task sets.
"""

from typing import List

from ai_platform.backend.domain_layer.business_logic.llm_benchmark.task_model import TaskSet
from ai_platform.backend.domain_layer.business_logic.llm_benchmark.task_sets import (
    get_task_set as _get_task_set,
)
from ai_platform.backend.domain_layer.business_logic.llm_benchmark.task_sets import (
    list_task_sets as _list_task_sets,
)


def get_task_set(name: str) -> TaskSet:
    """Task set by ``name`` or ``name@version``."""
    return _get_task_set(name)


def list_task_sets() -> List[str]:
    """Registered task set names."""
    return _list_task_sets()
