"""
Human review of screened benchmark answers.

The screening is a rule-based pre-assessment; this service closes the loop:

1. ``review_items`` selects records for a person to judge - by default every
   ``manual_review`` record, optionally plus a random sample of records the
   rules *did* decide (``sample_decided``), which is what makes it possible to
   measure how often the rules are right;
2. the person fills in a verdict per item (the UI layer writes and reads the
   spreadsheet);
3. ``apply_reviews`` writes the verdicts into a copy of the screening: the
   record's status becomes ``human_<verdict>`` and the rule's status is kept as
   ``automatic_status``;
4. ``screening_agreement`` compares rule and human on the reviewed decided
   records (confusion counts and agreement rate).

Verdicts: ``correct``, ``incorrect``, ``partial``, ``unclear``. Items are
matched by position *and* by (model, test_id, language, run_index), so a
review file cannot silently be applied to a different run.
"""

import copy
import random
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional

VERDICTS = ("correct", "incorrect", "partial", "unclear")
#: Human assessment of the reasoning shown, separate from the result: a right
#: result reached through wrong reasoning is still a defect.
REASONING_VERDICTS = ("correct", "incorrect", "none")


class ReviewError(ValueError):
    """Review file does not match the screening, or holds invalid verdicts."""


def record_key(record: Dict[str, Any]) -> str:
    """Stable identity of a benchmark record."""
    return "|".join(str(record.get(k)) for k in ("model", "test_id", "language", "run_index"))


def automatic_group(status: str) -> str:
    """Rule status -> correct / incorrect / partial / manual_review."""
    for group in ("correct", "incorrect", "partial"):
        if status.startswith(f"candidate_{group}"):
            return group
    return "manual_review"


def review_items(report: Dict[str, Any], screening: Dict[str, Any],
                 sample_decided: int = 0, seed: int = 0,
                 include_all: bool = False) -> List[Dict[str, Any]]:
    """Items for human review: all manual_review records plus a decided sample.

    ``include_all`` returns every record (a complete review sheet).
    """
    raw, screened = report.get("results", []), screening.get("results", [])
    if len(raw) != len(screened):
        raise ReviewError("screening does not belong to this report (record counts differ)")
    manual, decided = [], []
    for index, (record, row) in enumerate(zip(raw, screened)):
        assessment = row["automatic_assessment"]["answer_screening"]
        item = {
            "index": index, "key": record_key(record), "model": record.get("model"),
            "test_id": record.get("test_id"), "language": record.get("language"),
            "run_index": record.get("run_index"), "prompt": record.get("prompt", ""),
            "expected": record.get("expected", ""), "answer": record.get("answer", ""),
            "finish_reason": record.get("finish_reason"),
            "automatic_status": assessment["status"],
            "automatic_verdict": automatic_group(assessment["status"]),
            "evidence": assessment["evidence"],
            "verdict": "", "human_reasoning": "", "comment": "",
        }
        (manual if assessment["status"] == "manual_review" else decided).append(item)
    if include_all:
        return sorted(manual + decided, key=lambda item: item["index"])
    sample = random.Random(seed).sample(decided, min(sample_decided, len(decided)))
    return sorted(manual + sample, key=lambda item: item["index"])


def apply_reviews(screening: Dict[str, Any], reviews: Iterable[Dict[str, Any]],
                  reviewer: Optional[str] = None) -> Dict[str, Any]:
    """Copy of ``screening`` with human verdicts applied; empty verdicts are skipped.

    ``verdict`` is the human result; ``human_reasoning`` (optional) the human
    assessment of the reasoning. A row with only a reasoning keeps the rule's
    status and records the reasoning.
    """
    reviewed = copy.deepcopy(screening)
    rows = reviewed.get("results", [])
    applied = 0
    for review in reviews:
        verdict = str(review.get("verdict") or "").strip().lower()
        reasoning = str(review.get("human_reasoning") or "").strip().lower()
        if not verdict and not reasoning:
            continue
        if verdict and verdict not in VERDICTS:
            raise ReviewError(f"item {review.get('index')}: verdict {verdict!r} not in {VERDICTS}")
        if reasoning and reasoning not in REASONING_VERDICTS:
            raise ReviewError(f"item {review.get('index')}: reasoning {reasoning!r} not in "
                              f"{REASONING_VERDICTS}")
        index = int(review["index"])
        if index >= len(rows) or record_key(rows[index]) != review.get("key"):
            raise ReviewError(f"item {index}: key {review.get('key')!r} does not match the "
                              "screening - wrong review file?")
        assessment = rows[index]["automatic_assessment"]["answer_screening"]
        assessment.setdefault("automatic_status", assessment["status"])
        if reasoning:
            assessment["human_reasoning"] = reasoning
        if verdict:
            assessment.update(status=f"human_{verdict}", human_verdict=verdict,
                              is_final_judgement=True)
        assessment["human_comment"] = str(review.get("comment") or "")
        if reviewer:
            assessment["reviewer"] = reviewer
        applied += 1
    reviewed["human_review"] = {"applied": applied, "reviewer": reviewer,
                                "agreement": screening_agreement(reviewed)}
    return reviewed


def screening_agreement(reviewed: Dict[str, Any]) -> Dict[str, Any]:
    """Rule vs human on reviewed records the rules had decided."""
    pairs = Counter()
    for row in reviewed.get("results", []):
        assessment = row["automatic_assessment"]["answer_screening"]
        if "human_verdict" not in assessment:
            continue
        pairs[(automatic_group(assessment["automatic_status"]),
               assessment["human_verdict"])] += 1
    decided = {k: v for k, v in pairs.items() if k[0] != "manual_review"}
    agree = sum(v for (auto, human), v in decided.items() if auto == human)
    total = sum(decided.values())
    return {"decided_reviewed": total, "agreed": agree,
            "agreement_rate": round(agree / total, 3) if total else None,
            "manual_review_resolved": sum(v for k, v in pairs.items()
                                          if k[0] == "manual_review"),
            "confusion": {f"{auto}->{human}": v for (auto, human), v in sorted(pairs.items())}}
