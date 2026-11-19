"""
Screen a benchmark report's answers (integrated from
``config/test_env/test_30a_analysis_v4_2.py``).

Thin service over ``common.evaluation.answer_screening``: it adds the
provenance of the analysed report (task set, schema, creation time) so an
analysis can be traced back to the run it came from. Reading and writing
files is the caller's job.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ai_platform.backend.domain_layer.business_logic.llm_benchmark.task_model import (
    TaskSetError,
)
from ai_platform.backend.domain_layer.business_logic.llm_benchmark.task_sets import get_task_set
from ai_platform.common.evaluation.answer_screening import screen_report


def with_task_metadata(report: Dict[str, Any]) -> Dict[str, Any]:
    """Copy of ``report`` whose records carry the task's ``rejected`` phrases.

    Reports written before rejected phrases existed get them from the
    registered task set of the same name and version, so re-screening an old
    run applies today's task definition. Unknown task sets are left as they are.
    """
    try:
        task_set = get_task_set(f"{report.get('task_set')}@{report.get('task_set_version')}")
    except TaskSetError:
        return report
    tasks = {t.task_id: t for t in task_set.tasks}
    results = []
    for record in report.get("results", []):
        task = tasks.get(record.get("test_id"))
        if task and "rejected" not in record and record.get("language") in task.languages:
            record = {**record, "rejected": list(task.prompt(record["language"]).rejected)}
        results.append(record)
    return {**report, "results": results}


def screen_benchmark_report(report: Dict[str, Any],
                            source: Optional[str] = None) -> Dict[str, Any]:
    """Screening of ``report`` with provenance; ``report`` is not modified."""
    analysis = screen_report(with_task_metadata(report))
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "source_report": {k: report.get(k) for k in
                          ("schema", "task_set", "task_set_version", "created_at_utc",
                           "models", "languages", "repeats", "endpoint", "provider")},
        **analysis,
    }
