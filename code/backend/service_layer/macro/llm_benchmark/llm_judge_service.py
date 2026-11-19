"""
LLM-as-judge: a second, independent opinion on every benchmark answer.

A (preferably strong, remote) model reads the question, the expected answer
and the model's answer and returns one of the human verdicts - correct,
incorrect, partial, unclear - with a one-sentence reason. The judgements are
kept in their own file, keyed by record (model|test_id|language|run_index),
so they never overwrite the rule screening or the human review; the review
spreadsheet shows them in the "LLM verdict" column.

Runs are resumable: records already judged in the output are skipped, so an
interrupted run continues where it stopped. Calls run in a small thread pool.

The judge is any LLM adapter with ``chat_completion`` (Anthropic, OpenAI,
Bedrock, an OpenAI-compatible server ...). Its verdict is an opinion, not a
ground truth: ``judge_agreement`` measures it against the human verdicts.
"""

import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from ai_platform.backend.service_layer.macro.llm_benchmark.review_service import (
    VERDICTS,
    record_key,
)
from ai_platform.common.llm.llm_exception import LLMError

JUDGE_SCHEMA = "ai_platform.llm_judge/1"
JUDGE_PROMPT = """You grade answers of language models in a benchmark. Judge only whether \
the ANSWER is right for the QUESTION, using the EXPECTED answer as the reference. \
The answer may be in Polish or English.

Verdicts:
- correct: the final answer matches the expected one (wording, units and language may differ);
- incorrect: the final answer is wrong, contradicts the expected one, or is missing while \
the text is coherent;
- partial: the final answer is right but the reasoning shown contains a real error, or only \
part of a multi-part answer is right;
- unclear: the text is incoherent, or it is cut off before any answer.

Reply with ONLY a JSON object: {{"verdict": "<correct|incorrect|partial|unclear>", \
"reason": "<one short sentence>"}}

QUESTION:
{question}

EXPECTED:
{expected}

ANSWER:
{answer}
"""
_JSON = re.compile(r"\{.*\}", re.S)


def parse_judgement(text: str) -> Dict[str, Any]:
    """{"verdict", "reason"} from the judge's reply; unparsable -> verdict None."""
    match = _JSON.search(text or "")
    try:
        data = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        data = {}
    verdict = str(data.get("verdict", "")).strip().lower()
    if verdict not in VERDICTS:
        return {"verdict": None, "reason": f"unparsable judge reply: {(text or '')[:200]}"}
    return {"verdict": verdict, "reason": str(data.get("reason", ""))[:500]}


def judge_record(judge, record: Dict[str, Any]) -> Dict[str, Any]:
    """One judgement (errors are recorded, not raised)."""
    if record.get("status") != "PASS":
        return {"verdict": "unclear", "reason": f"no answer: {record.get('error')}"}
    prompt = JUDGE_PROMPT.format(question=record.get("prompt", ""),
                                 expected=record.get("expected", ""),
                                 answer=record.get("answer", ""))
    try:
        reply = judge.chat_completion([{"role": "user", "content": prompt}],
                                      temperature=0, max_tokens=200)
    except LLMError as exc:
        return {"verdict": None, "reason": f"judge error: {type(exc).__name__}: {exc}"}
    return parse_judgement(reply.text)


def judge_report(report: Dict[str, Any], judge, judge_name: str, *,  # pylint: disable=too-many-arguments,too-many-locals
                 existing: Optional[Dict[str, Any]] = None, workers: int = 4,
                 progress: Callable[[str], None] = lambda m: None,
                 save: Callable[[Dict[str, Any]], None] = lambda d: None) -> Dict[str, Any]:
    """Judge every record not yet judged; ``save`` is called after each batch."""
    data = existing or {"schema": JUDGE_SCHEMA, "judge": judge_name, "judgements": {}}
    if data.get("judge") != judge_name:
        raise ValueError(f"existing judgements are by {data.get('judge')!r}, not {judge_name!r}")
    done = data["judgements"]
    todo = [r for r in report.get("results", [])
            if record_key(r) not in done or done[record_key(r)].get("verdict") is None]
    progress(f"{len(todo)} records to judge ({len(done)} already judged)")
    batch = max(1, workers * 5)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for start in range(0, len(todo), batch):
            chunk = todo[start:start + batch]
            for record, judgement in zip(chunk, pool.map(lambda r: judge_record(judge, r),
                                                          chunk)):
                done[record_key(record)] = judgement
            data["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
            save(data)
            progress(f"  {min(start + batch, len(todo))}/{len(todo)} judged")
    return data


def judge_agreement(judgements: Dict[str, Any], reviewed: Dict[str, Any]) -> Dict[str, Any]:
    """LLM judge vs human verdicts on records both have judged."""
    pairs: Dict[str, int] = {}
    for row in reviewed.get("results", []):
        human = row["automatic_assessment"]["answer_screening"].get("human_verdict")
        llm = (judgements.get("judgements", {}).get(record_key(row)) or {}).get("verdict")
        if human and llm:
            pairs[f"{llm}->{human}"] = pairs.get(f"{llm}->{human}", 0) + 1
    total = sum(pairs.values())
    agreed = sum(v for k, v in pairs.items() if k.split("->")[0] == k.split("->")[1])
    return {"compared": total, "agreed": agreed,
            "agreement_rate": round(agreed / total, 3) if total else None,
            "confusion": dict(sorted(pairs.items()))}


def judgement_columns(judgements: Optional[Dict[str, Any]],
                      items: List[Dict[str, Any]]) -> None:
    """Add llm_verdict / llm_reason to review items (in place)."""
    table = (judgements or {}).get("judgements", {})
    for item in items:
        found = table.get(item["key"]) or {}
        item["llm_verdict"] = found.get("verdict") or ""
        item["llm_reason"] = found.get("reason") or ""
