"""
Aggregate a benchmark report and its screening into comparison tables.

The output is presentation-neutral (plain dicts and lists); the UI layer
renders it as HTML or Markdown. Three views:

- ``models``: per model and language - answers received, latency (median,
  90th percentile), truncations, and screening outcome counts grouped as
  correct / incorrect / partial / manual review;
- ``tasks``: per task, language and model - the screening outcome of every
  run, and whether the runs agree (temperature 0 should make them agree;
  disagreement points at nondeterminism in the runtime);
- ``warmup``: per model - load + first answer time.

Outcome groups are taken from the status prefix, so new checker statuses
and human verdicts (``human_correct`` ...) fall into the right group.
"""

import statistics
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional

GROUPS = ("correct", "incorrect", "partial", "manual_review")


def outcome_group(status: str) -> str:
    """Map a screening status (rule ``candidate_*`` or ``human_*``) to one of GROUPS.

    A human ``unclear`` stays in manual_review.
    """
    for group in ("correct", "incorrect", "partial"):
        if status.startswith((f"candidate_{group}", f"human_{group}")):
            return group
    return "manual_review"


def percentile(values: List[float], fraction: float) -> Optional[float]:
    """Nearest-rank percentile (None for no values)."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, round(fraction * len(ordered)))
    return ordered[min(rank, len(ordered)) - 1]


def summarize_benchmark(report: Dict[str, Any], screening: Dict[str, Any]) -> Dict[str, Any]:  # pylint: disable=too-many-locals
    """Comparison tables for ``report`` screened as ``screening``."""
    screened = screening.get("results", [])
    if len(screened) != len(report.get("results", [])):
        raise ValueError("screening does not belong to this report (record counts differ)")

    cells: Dict[tuple, Dict[str, Any]] = defaultdict(lambda: {
        "answered": 0, "requests": 0, "times": [], "truncated": 0, "groups": Counter()})
    tasks: Dict[tuple, List[str]] = defaultdict(list)

    for raw, row in zip(report["results"], screened):
        key = (raw["model"], raw["language"])
        cell = cells[key]
        cell["requests"] += 1
        if raw.get("status") == "PASS":
            cell["answered"] += 1
            cell["times"].append(raw["elapsed_seconds"])
        cell["truncated"] += raw.get("finish_reason") == "length"
        status = row["automatic_assessment"]["answer_screening"]["status"]
        cell["groups"][outcome_group(status)] += 1
        tasks[(raw["test_id"], raw["language"], raw["model"])].append(status)

    models = []
    for (model, language), cell in cells.items():
        times = cell["times"]
        models.append({
            "model": model, "language": language,
            "answered": cell["answered"], "requests": cell["requests"],
            "median_seconds": round(statistics.median(times), 2) if times else None,
            "p90_seconds": round(percentile(times, 0.9), 2) if times else None,
            "truncated": cell["truncated"],
            **{group: cell["groups"][group] for group in GROUPS},
        })
    models.sort(key=lambda r: (-r["correct"], r["incorrect"], r["model"], r["language"]))

    task_rows = [{"task": task, "language": language, "model": model, "runs": statuses,
                  "consistent": len(set(statuses)) == 1,
                  "majority": Counter(statuses).most_common(1)[0][0]}
                 for (task, language, model), statuses in sorted(tasks.items())]

    warmup = [{"model": model, **info} for model, info in (report.get("warmup") or {}).items()]
    return {
        "task_set": f"{report.get('task_set')}@{report.get('task_set_version')}",
        "created_at_utc": report.get("created_at_utc"),
        "provider": report.get("provider"), "endpoint": report.get("endpoint"),
        "repeats": report.get("repeats"), "temperature": report.get("temperature"),
        "max_tokens": report.get("max_tokens"),
        "screening_version": screening.get("screening_version"),
        "models": models, "tasks": task_rows, "warmup": warmup,
        "inconsistent_runs": sum(not row["consistent"] for row in task_rows),
    }
