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

from ai_platform.common.evaluation.answer_screening import screen_report


def screen_benchmark_report(report: Dict[str, Any],
                            source: Optional[str] = None) -> Dict[str, Any]:
    """Screening of ``report`` with provenance; ``report`` is not modified."""
    analysis = screen_report(report)
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "source_report": {k: report.get(k) for k in
                          ("schema", "task_set", "task_set_version", "created_at_utc",
                           "models", "languages", "repeats", "endpoint", "provider")},
        **analysis,
    }
