"""
LLM-as-judge: a second, independent opinion on every benchmark answer.

A (preferably strong, remote) model reads the question, the expected answer
and the model's answer and returns TWO separate assessments, because a right
result reached through wrong reasoning (e.g. two errors cancelling out) is
still a defect worth reporting:

- ``result``: correct / partial / incorrect / unclear - the final answer only
  (partial: only part of a multi-part answer is right; incoherent, looping or
  refusing text is incorrect; unclear: cut off before any answer);
- ``reasoning``: correct / incorrect / none - the reasoning shown (incorrect:
  at least one real error, even when the result is right; none: bare answer);

plus a short ``reason`` naming the error. The judgements are kept in their
own file, keyed by record (model|test_id|language|run_index), so they never
overwrite the rule screening or the human review; the review spreadsheet
shows them in the "LLM result" and "LLM reasoning" columns.

Schema 1 files (one ``verdict`` per record, before 2026-11-23) are converted
locally by ``migrate_judgements`` - no tokens: correct -> result correct;
partial -> result correct, reasoning incorrect; incorrect -> result incorrect,
reasoning not_assessed; unclear -> incorrect for incoherent text, unclear when
cut off. The old verdict is kept as ``legacy_verdict``.

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

JUDGE_SCHEMA = "ai_platform.llm_judge/2"
LEGACY_SCHEMA = "ai_platform.llm_judge/1"
RESULTS = ("correct", "partial", "incorrect", "unclear")
REASONINGS = ("correct", "incorrect", "none")
#: Only in records converted from schema 1, whose verdict said nothing about reasoning.
NOT_ASSESSED = "not_assessed"
#: Answers shorter than this (characters) count as showing no reasoning.
BARE_ANSWER_CHARS = 80
JUDGE_PROMPT = """You grade answers of language models in a benchmark. Judge only whether \
the ANSWER is right for the QUESTION, using the EXPECTED answer as the reference. \
The answer may be in Polish or English.

Assess two things separately - a right result reached through wrong reasoning \
is still a defect.

result (the final answer only):
- correct: matches the expected answer (wording, units and language may differ);
- partial: the question has several parts and only some are answered right;
- incorrect: wrong, contradicts the expected answer, missing, a refusal, or the text is \
incoherent or looping;
- unclear: the text is cut off before giving any answer.

reasoning (the explanation or calculation shown):
- correct: no real error;
- incorrect: at least one real error - a wrong fact, a wrong calculation step, a \
contradiction - even if the result is right;
- none: no reasoning shown, only the answer.

Reply with ONLY a JSON object: {{"result": "<correct|partial|incorrect|unclear>", \
"reasoning": "<correct|incorrect|none>", "reason": "<at most 20 words; name the error if any>"}}

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

Assess two things separately - a right result reached through wrong reasoning \
is still a defect.

result (the final answer only):
- correct: matches the expected answer (wording, units and language may differ);
- partial: the question has several parts and only some are answered right;
- incorrect: wrong, contradicts the expected answer, missing, a refusal, or the text is \
incoherent or looping;
- unclear: the text is cut off before giving any answer.

reasoning (the explanation or calculation shown):
- correct: no real error;
- incorrect: at least one real error - a wrong fact, a wrong calculation step, a \
contradiction - even if the result is right;
- none: no reasoning shown, only the answer.

Reply with ONLY a JSON array, one object per answer, in any order:
[{{"id": "<answer id>", "result": "<correct|partial|incorrect|unclear>", \
"reasoning": "<correct|incorrect|none>", "reason": "<at most 20 words; name the error if any>"}}]

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


def _pending(reason: str) -> Dict[str, Any]:
    """A record not judged (yet): result None is retried by the next run."""
    return {"result": None, "reasoning": None, "reason": reason}


def is_judged(judgement: Optional[Dict[str, Any]]) -> bool:
    """True when ``judgement`` holds a result (schema 2) or a verdict (schema 1)."""
    return bool(judgement) and (judgement.get("result") or judgement.get("verdict")) is not None


def parse_judgement(text: str) -> Dict[str, Any]:
    """{"result", "reasoning", "reason"} from the judge's reply; unparsable -> result None.

    A reply in the schema 1 form ({"verdict": ...}) is converted as in
    ``migrate_judgement``.
    """
    match = _JSON.search(text or "")
    try:
        data = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    if "result" not in data and str(data.get("verdict", "")).strip().lower() in VERDICTS:
        return migrate_judgement({"verdict": str(data["verdict"]).strip().lower(),
                                  "reason": str(data.get("reason", ""))[:500]})
    result = str(data.get("result", "")).strip().lower()
    reasoning = str(data.get("reasoning", "")).strip().lower()
    if result not in RESULTS or reasoning not in REASONINGS:
        return _pending(f"unparsable judge reply: {(text or '')[:200]}")
    return {"result": result, "reasoning": reasoning, "reason": str(data.get("reason", ""))[:500]}


_CUT_OFF = re.compile(r"cut off|truncat|urwan|ucięt|przerwan", re.I)
_INCOHERENT = re.compile(r"incoheren|niespójn|zapętl|repetit|chaot|nonsens|bezsens", re.I)


def migrate_judgement(old: Dict[str, Any], answer: Optional[str] = None) -> Dict[str, Any]:
    """Schema 1 judgement (one ``verdict``) as schema 2, locally and without a call.

    ``answer`` (the judged text) only decides correct -> reasoning correct or none.
    """
    if "result" in old or old.get("verdict") is None:
        return {k: v for k, v in old.items() if k != "verdict"} if "result" in old \
            else _pending(old.get("reason", ""))
    verdict, reason = old["verdict"], old.get("reason", "")
    if verdict == "correct":
        bare = answer is not None and len(str(answer).strip()) < BARE_ANSWER_CHARS
        new = {"result": "correct", "reasoning": "none" if bare else "correct"}
    elif verdict == "partial":  # schema 1 used it for "right result, error in reasoning"
        new = {"result": "correct", "reasoning": "incorrect"}
    elif verdict == "incorrect":
        new = {"result": "incorrect", "reasoning": NOT_ASSESSED}
    else:  # unclear: incoherent text is incorrect now; only a cut-off answer stays unclear
        cut_only = _CUT_OFF.search(reason) and not _INCOHERENT.search(reason)
        new = {"result": "unclear" if cut_only else "incorrect", "reasoning": NOT_ASSESSED}
    return {**new, "reason": reason, "legacy_verdict": verdict}


def migrate_judgements(data: Dict[str, Any],
                       report: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Judgement file converted to schema 2 (unchanged if already there)."""
    if data.get("schema") == JUDGE_SCHEMA:
        return data
    answers = {record_key(r): r.get("answer") for r in (report or {}).get("results", [])}
    migrated = {key: migrate_judgement(old, answers.get(key))
                for key, old in data.get("judgements", {}).items()}
    return {**data, "schema": JUDGE_SCHEMA, "judgements": migrated,
            "migrated_from": data.get("schema", LEGACY_SCHEMA),
            "migrated_at_utc": datetime.now(timezone.utc).isoformat()}


def judge_record(judge, record: Dict[str, Any]) -> Dict[str, Any]:
    """One judgement (errors are recorded, not raised)."""
    if record.get("status") != "PASS":
        return {"result": "unclear", "reasoning": "none",
                "reason": f"no answer: {record.get('error')}"}
    prompt = JUDGE_PROMPT.format(question=record.get("prompt", ""),
                                 expected=record.get("expected", ""),
                                 answer=record.get("answer", ""))
    try:
        reply = judge.chat_completion([{"role": "user", "content": prompt}],
                                      temperature=0, max_tokens=200)
    except LLMError as exc:
        return _pending(f"judge error: {type(exc).__name__}: {exc}")
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
            return [_pending(f"judge error: {type(exc).__name__}: {exc}") for _ in records]
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
                       _pending("missing in the judge's batch reply"))
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
            if not is_judged(done.get(record_key(r)))
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
    data = migrate_judgements(existing, report) if existing else \
        {"schema": JUDGE_SCHEMA, "judge": judge_name, "judgements": {}}
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


def judgement_counts(data: Dict[str, Any], report: Optional[Dict[str, Any]] = None,
                     field: str = "result") -> Dict[str, int]:
    """Counts of ``field`` (result or reasoning); not judged yet as 'pending'.

    With ``report`` every record of the report is counted, judged or not.
    """
    table = data.get("judgements", {})
    keys = [record_key(r) for r in report.get("results", [])] if report else list(table)
    counts: Dict[str, int] = {}
    for key in keys:
        value = (table.get(key) or {}).get(field) or "pending"
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _agreement(pairs: Dict[str, int]) -> Dict[str, Any]:
    total = sum(pairs.values())
    agreed = sum(v for k, v in pairs.items() if k.split("->")[0] == k.split("->")[1])
    return {"compared": total, "agreed": agreed,
            "agreement_rate": round(agreed / total, 3) if total else None,
            "confusion": dict(sorted(pairs.items()))}


def judge_agreement(judgements: Dict[str, Any], reviewed: Dict[str, Any]) -> Dict[str, Any]:
    """LLM judge vs human, on records both have judged: result and reasoning.

    ``result`` compares the judge's result with the human verdict; ``reasoning``
    the judge's reasoning with the human reasoning, where the person gave one
    (records converted from schema 1 with reasoning not_assessed are left out).
    """
    table = migrate_judgements(judgements).get("judgements", {})
    result: Dict[str, int] = {}
    reasoning: Dict[str, int] = {}
    for row in reviewed.get("results", []):
        assessment = row["automatic_assessment"]["answer_screening"]
        llm = table.get(record_key(row)) or {}
        human, llm_result = assessment.get("human_verdict"), llm.get("result")
        if human and llm_result:
            result[f"{llm_result}->{human}"] = result.get(f"{llm_result}->{human}", 0) + 1
        human_r, llm_r = assessment.get("human_reasoning"), llm.get("reasoning")
        if human_r and llm_r and llm_r != NOT_ASSESSED:
            reasoning[f"{llm_r}->{human_r}"] = reasoning.get(f"{llm_r}->{human_r}", 0) + 1
    return {**_agreement(result), "reasoning": _agreement(reasoning)}


def judgement_columns(judgements: Optional[Dict[str, Any]],
                      items: List[Dict[str, Any]]) -> None:
    """Add llm_result / llm_reasoning / llm_reason to review items (in place)."""
    table = migrate_judgements(judgements or {}).get("judgements", {})
    for item in items:
        found = table.get(item["key"]) or {}
        item["llm_result"] = found.get("result") or ""
        item["llm_reasoning"] = found.get("reasoning") or ""
        item["llm_reason"] = found.get("reason") or ""
