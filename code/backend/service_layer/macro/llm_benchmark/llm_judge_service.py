"""
LLM-as-judge: a second, independent opinion on every benchmark answer.

A (preferably strong, remote) model reads the question, the expected answer
and the model's answer and returns one of the human verdicts - correct,
incorrect, partial, unclear - with a one-sentence reason. The judgements are
kept in their own file, keyed by record (model|test_id|language|run_index),
so they never overwrite the rule screening or the human review; the review
spreadsheet shows them in the "LLM verdict" column.

Batched by default: all answers to the same question (same task and
language - 22 answers for 11 models x 2 runs) go to the judge in ONE prompt,
with the question and the expected answer stated once. For the v3 run that is
32 prompts instead of 704. ``scope="undecided"`` judges only the records the
rules sent to manual review. ``estimate`` reports prompts and approximate
tokens before anything is sent.

Runs are resumable: records already judged in the output are skipped, so an
interrupted run continues where it stopped; answers a batch reply missed are
retried in the next run. Calls run in a small thread pool.

The judge is any LLM adapter with ``chat_completion`` (Anthropic, OpenAI,
Bedrock, an OpenAI-compatible server ...). Its verdict is an opinion, not a
ground truth: ``judge_agreement`` measures it against the human verdicts.
"""

import json
import re
import time
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
_JSON_ARRAY = re.compile(r"\[.*\]", re.S)

BATCH_PROMPT = """You grade answers of language models in a benchmark. All answers below \
respond to the same QUESTION; judge each one independently, using the EXPECTED answer as \
the reference. Answers may be in Polish or English.

Verdicts:
- correct: the final answer matches the expected one (wording, units and language may differ);
- incorrect: the final answer is wrong, contradicts the expected one, or is missing while \
the text is coherent;
- partial: the final answer is right but the reasoning shown contains a real error, or only \
part of a multi-part answer is right;
- unclear: the text is incoherent, or it is cut off before any answer.

Reply with ONLY a JSON array, one object per answer, in any order:
[{{"id": "<answer id>", "verdict": "<correct|incorrect|partial|unclear>", \
"reason": "<at most 15 words>"}}]

QUESTION:
{question}

EXPECTED:
{expected}

ANSWERS:
{answers}
"""
#: Extra output tokens per batch for "thinking" models (Gemini 3.x, gpt-oss): their
#: hidden reasoning counts against max_tokens, and a cut reply loses the JSON array.
#: Kept moderate: some providers count max_tokens against a per-minute token
#: limit (Groq free tier: 8000 TPM per request), so a big reserve gets HTTP 413.
THINKING_RESERVE = 2000
#: Longest answer text sent to the judge (characters); longer ones are cut with a mark.
MAX_ANSWER_CHARS = 3000


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


def _clip(text: str) -> str:
    text = str(text or "")
    return text if len(text) <= MAX_ANSWER_CHARS else \
        text[:MAX_ANSWER_CHARS] + f" [... cut, {len(text)} characters in total]"


def batch_prompt(records: List[Dict[str, Any]]) -> str:
    """One prompt for answers to the same question; ids are A1, A2, ..."""
    answers = "\n\n".join(f"--- id: A{n} ---\n{_clip(r.get('answer'))}"
                           for n, r in enumerate(records, start=1))
    return BATCH_PROMPT.format(question=records[0].get("prompt", ""),
                               expected=records[0].get("expected", ""), answers=answers)


#: HTTP statuses worth retrying: rate limit, overload, gateway trouble.
RETRY_STATUSES = (429, 500, 502, 503, 504)
#: Waits (seconds) before the 1st, 2nd, ... retry of a batch.
RETRY_DELAYS = (20.0, 60.0, 120.0)


def _is_daily_quota(exc: Exception) -> bool:
    """A per-day quota (waiting minutes does not help, unlike a per-minute one)."""
    text = str(exc).lower()
    return "per day" in text or "perday" in text


def judge_batch(judge, records: List[Dict[str, Any]], *,  # pylint: disable=too-many-arguments,too-many-locals
                retries: int = len(RETRY_DELAYS), reserve: int = THINKING_RESERVE,
                sleep: Callable[[float], None] = time.sleep) -> List[Dict[str, Any]]:
    """Judgements for answers to one question, in the order of ``records``.

    Transient errors (``RETRY_STATUSES``, e.g. "model is experiencing high
    demand") are retried after ``RETRY_DELAYS``, except a per-day quota.
    HTTP 413 (request too large for the provider's limit) splits the batch in
    halves, down to single answers. Other errors fail at once.
    """
    attempt = 0
    while True:
        try:
            reply = judge.chat_completion(
                [{"role": "user", "content": batch_prompt(records)}],
                temperature=0, max_tokens=120 * len(records) + reserve)
            break
        except LLMError as exc:
            status = getattr(exc, "status", None)
            if status == 413 and len(records) > 1:
                half = len(records) // 2
                return (judge_batch(judge, records[:half], retries=retries, reserve=reserve,
                                    sleep=sleep)
                        + judge_batch(judge, records[half:], retries=retries, reserve=reserve,
                                      sleep=sleep))
            if status in RETRY_STATUSES and attempt < retries and not _is_daily_quota(exc):
                sleep(RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)])
                attempt += 1
                continue
            error = {"verdict": None, "reason": f"judge error: {type(exc).__name__}: {exc}"}
            return [dict(error) for _ in records]
    match = _JSON_ARRAY.search(reply.text or "")
    try:
        items = json.loads(match.group(0)) if match else []
    except json.JSONDecodeError:
        items = []
    by_id = {str(i.get("id")): i for i in items if isinstance(i, dict)}
    results = []
    for number in range(1, len(records) + 1):
        item = by_id.get(f"A{number}")
        results.append(parse_judgement(json.dumps(item)) if item else
                       {"verdict": None, "reason": "missing in the judge's batch reply"})
    return results


def _groups(records: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """Answered records grouped by question (task + language), in report order."""
    groups: Dict[tuple, List[Dict[str, Any]]] = {}
    for record in records:
        groups.setdefault((record.get("test_id"), record.get("language")), []).append(record)
    return list(groups.values())


def select_records(report: Dict[str, Any], screening: Optional[Dict[str, Any]],
                   done: Dict[str, Any], scope: str = "all") -> List[Dict[str, Any]]:
    """Records still to judge; ``scope='undecided'`` keeps only manual_review ones."""
    if scope not in ("all", "undecided"):
        raise ValueError("scope must be 'all' or 'undecided'")
    undecided = None
    if scope == "undecided":
        if screening is None:
            raise ValueError("scope 'undecided' needs the screening")
        undecided = {record_key(r) for r in screening.get("results", [])
                     if r["automatic_assessment"]["answer_screening"]["status"]
                     == "manual_review"}
    return [r for r in report.get("results", [])
            if (record_key(r) not in done or done[record_key(r)].get("verdict") is None)
            and (undecided is None or record_key(r) in undecided)]


def estimate(records: List[Dict[str, Any]], batched: bool = True) -> Dict[str, Any]:
    """Prompts and approximate tokens (characters / 4) a judge run would send."""
    answered = [r for r in records if r.get("status") == "PASS"]
    if batched:
        prompts = [batch_prompt(g) for g in _groups(answered)]
        output = 25 * len(answered)
    else:
        prompts = [JUDGE_PROMPT.format(question=r.get("prompt", ""),
                                       expected=r.get("expected", ""),
                                       answer=r.get("answer", "")) for r in answered]
        output = 40 * len(answered)
    return {"records": len(records), "prompts": len(prompts),
            "approx_input_tokens": sum(len(p) for p in prompts) // 4,
            "approx_output_tokens": output}


def judge_report(report: Dict[str, Any], judge, judge_name: str, *,  # pylint: disable=too-many-arguments,too-many-locals
                 existing: Optional[Dict[str, Any]] = None, workers: int = 4,
                 screening: Optional[Dict[str, Any]] = None, scope: str = "all",
                 batched: bool = True, pause: float = 0.0,
                 retries: int = len(RETRY_DELAYS), reserve: int = THINKING_RESERVE,
                 sleep: Callable[[float], None] = time.sleep,
                 progress: Callable[[str], None] = lambda m: None,
                 save: Callable[[Dict[str, Any]], None] = lambda d: None) -> Dict[str, Any]:
    """Judge the records not yet judged; ``save`` is called after each round.

    ``pause`` seconds are waited between rounds (free tiers limit requests per
    minute). A round in which every call failed stops the run - typically a
    quota or key problem, which the remaining prompts would only repeat.
    """
    data = existing or {"schema": JUDGE_SCHEMA, "judge": judge_name, "judgements": {}}
    if data.get("judge") != judge_name:
        raise ValueError(f"existing judgements are by {data.get('judge')!r}, not {judge_name!r}")
    done = data["judgements"]
    todo = select_records(report, screening, done, scope)
    for record in todo:  # nothing to judge: recorded without a call
        if record.get("status") != "PASS":
            done[record_key(record)] = judge_record(judge, record)
    todo = [r for r in todo if r.get("status") == "PASS"]
    units = _groups(todo) if batched else [[r] for r in todo]
    progress(f"{len(todo)} answers to judge in {len(units)} prompts "
             f"({len(done)} already judged)")

    def run(unit):
        if batched:
            return judge_batch(judge, unit, retries=retries, reserve=reserve, sleep=sleep)
        return [judge_record(judge, unit[0])]

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for start in range(0, len(units), max(1, workers)):
            chunk = units[start:start + max(1, workers)]
            for unit, judgements in zip(chunk, pool.map(run, chunk)):
                for record, judgement in zip(unit, judgements):
                    done[record_key(record)] = judgement
            data["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
            save(data)
            progress(f"  {min(start + len(chunk), len(units))}/{len(units)} prompts")
            failed = [done[record_key(r)] for unit in chunk for r in unit]
            if all(str(j.get("reason", "")).startswith("judge error") for j in failed):
                progress(f"stopped: every call in this round failed - {failed[0]['reason'][:300]}")
                break
            if pause and start + len(chunk) < len(units):
                sleep(pause)
    return data


def judgement_counts(data: Dict[str, Any],
                     report: Optional[Dict[str, Any]] = None) -> Dict[str, int]:
    """Verdict counts; not judged yet (after an error, or never tried) as 'pending'.

    With ``report`` every record of the report is counted, judged or not.
    """
    table = data.get("judgements", {})
    keys = [record_key(r) for r in report.get("results", [])] if report else list(table)
    counts: Dict[str, int] = {}
    for key in keys:
        verdict = (table.get(key) or {}).get("verdict") or "pending"
        counts[verdict] = counts.get(verdict, 0) + 1
    return dict(sorted(counts.items()))


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
