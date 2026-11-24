"""Unit tests of the LLM benchmark domain, runner and CLI (no model server needed)."""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))

from fake_json_server import FakeJsonServer, openai_chat_answer  # noqa: E402

from ai_platform.backend.domain_layer.business_logic.llm_benchmark.task_model import (  # noqa: E402
    TaskSet,
    TaskSetError,
    task_from_dict,
)
from ai_platform.backend.domain_layer.business_logic.llm_benchmark.task_sets import (  # noqa: E402
    get_task_set,
)
from ai_platform.backend.service_layer.macro.llm_benchmark.benchmark_runner import (  # noqa: E402
    REPORT_SCHEMA,
    LLMBenchmarkRunner,
)
from ai_platform.backend.service_layer.macro.llm_benchmark.screening_service import (  # noqa: E402
    screen_benchmark_report,
)
from ai_platform.backend.ui_layer.cli import llm_benchmark_cli  # noqa: E402
from ai_platform.common.llm.chat_result import ChatResult  # noqa: E402
from ai_platform.common.llm.llm_exception import LLMConnectionError  # noqa: E402


class ScriptedLLM:
    """Answers each prompt with a scripted text; can fail on demand."""

    def __init__(self, model, answers, fail_on=()):
        self.model = model
        self.answers = answers
        self.fail_on = fail_on
        self.closed = False

    def chat_completion(self, messages, **_):
        """Scripted answer by prompt substring."""
        prompt = messages[0]["content"]
        if any(marker in prompt for marker in self.fail_on):
            raise LLMConnectionError("down")
        text = next((a for key, a in self.answers.items() if key in prompt), "OK")
        return ChatResult(text=text, model=self.model, finish_reason="stop",
                          usage={"total_tokens": 3}, elapsed_seconds=0.5)

    def shutdown(self):
        """Record shutdown."""
        self.closed = True


def test_builtin_task_set_and_validation():
    task_set = get_task_set("bilingual_reasoning@2")
    assert get_task_set("bilingual_reasoning") is get_task_set("bilingual_reasoning@3")
    assert task_set.languages == ["pl", "en"]
    assert {t.checker for t in task_set.tasks} == {
        "multiplication", "percentage", "syllogism", "currency_vs_cpi"}
    v3 = get_task_set("bilingual_reasoning")
    assert len(v3.tasks) == 16 and v3.languages == ["pl", "en"]
    assert {t.checker for t in v3.tasks} >= {"numeric", "yes_no", "phrase"}
    with pytest.raises(TaskSetError):
        task_set.select(["de"])
    with pytest.raises(TaskSetError):
        TaskSet("x", "1", [])
    with pytest.raises(TaskSetError):
        task_from_dict({"id": "x"})


def test_runner_records_results_failures_and_shuts_down():
    created = {}

    def factory(model):
        created[model] = ScriptedLLM(model, {"17": "17 * 23 = 391"},
                                     fail_on=("USD/PLN",) if model == "b" else ())
        return created[model]

    report = LLMBenchmarkRunner(factory).run(get_task_set("bilingual_reasoning@2"), ["a", "b"],
                                             languages=["pl"], repeats=2)
    assert report["schema"] == REPORT_SCHEMA
    assert report["warmup"]["a"]["status"] == "PASS"
    assert len(report["results"]) == 2 * 4 * 2
    failed = [r for r in report["results"] if r["status"] == "FAIL"]
    assert len(failed) == 2 and {r["model"] for r in failed} == {"b"}
    assert failed[0]["error_type"] == "LLMConnectionError"
    assert report["summary"]["a [PL]"]["technical_pass"] == 8
    assert all(llm.closed for llm in created.values())

    analysis = screen_benchmark_report(report, source="mem")
    statuses = [r["automatic_assessment"]["answer_screening"]["status"]
                for r in analysis["results"] if r["test_id"] == "arithmetic_multiplication"]
    assert set(statuses) == {"candidate_correct_result_only"}
    assert analysis["source_report"]["task_set"] == "bilingual_reasoning"


def test_runner_skips_model_whose_warmup_fails():
    report = LLMBenchmarkRunner(lambda m: ScriptedLLM(m, {}, fail_on=("OK.",))).run(
        get_task_set("bilingual_reasoning@2"), ["x"], repeats=1)
    assert report["warmup"]["x"]["status"] == "FAIL" and report["results"] == []


def test_runner_argument_validation():
    runner = LLMBenchmarkRunner(lambda m: ScriptedLLM(m, {}))
    with pytest.raises(ValueError):
        runner.run(get_task_set("bilingual_reasoning@2"), [], repeats=1)
    with pytest.raises(ValueError):
        runner.run(get_task_set("bilingual_reasoning@2"), ["m"], repeats=0)


def test_cli_run_and_screen_against_fake_server(tmp_path, capsys):
    with FakeJsonServer({("POST", "/v1/chat/completions"):
                         openai_chat_answer("17 * 23 = 391")}) as server:
        code = llm_benchmark_cli.main([
            "run", "--provider", "openai-compatible", "--base-url", server.url,
            "--models", "m", "--languages", "en", "--repeats", "1",
            "--task-set", "bilingual_reasoning@2",
            "--output", str(tmp_path / "r.json"), "--screen"])
    assert code == 0
    written = capsys.readouterr().out.split()
    assert written == [str(tmp_path / "r.json"), str(tmp_path / "r_screening.json")]
    report = json.loads((tmp_path / "r.json").read_text(encoding="utf-8"))
    assert report["provider"] == "openai-compatible" and len(report["results"]) == 4

    assert llm_benchmark_cli.main(["screen", str(tmp_path / "r.json"),
                                   "--output", str(tmp_path / "s.json")]) == 0
    assert json.loads((tmp_path / "s.json").read_text())["summary"]["records"] == 4


def test_cli_exit_status_when_nothing_answers(tmp_path):
    code = llm_benchmark_cli.main(["run", "--provider", "openai-compatible",
                                   "--base-url", "http://127.0.0.1:9", "--models", "m",
                                   "--repeats", "1", "--timeout", "2",
                                   "--output", str(tmp_path / "r.json")])
    assert code == 1


def test_summary_and_rendering(tmp_path):
    from ai_platform.backend.service_layer.macro.llm_benchmark.benchmark_summary import (  # pylint: disable=import-outside-toplevel
        outcome_group,
        percentile,
        summarize_benchmark,
    )
    from ai_platform.backend.ui_layer.cli.benchmark_report_rendering import (  # pylint: disable=import-outside-toplevel
        render_html,
        render_markdown,
    )

    answers = {"17": "17 * 23 = 391", "112": "12%", "Mruczek": "Tak, Mruczek jest ssakiem.",
               "USD/PLN": "Wzrost USD/PLN automatycznie powoduje wzrost CPI."}
    report = LLMBenchmarkRunner(lambda m: ScriptedLLM(m, answers)).run(
        get_task_set("bilingual_reasoning@2"), ["<b>m&1</b>"], languages=["pl"], repeats=2,
        metadata={"provider": "test", "endpoint": "mem"})
    summary = summarize_benchmark(report, screen_benchmark_report(report))
    row = summary["models"][0]
    assert (row["correct"], row["incorrect"], row["manual_review"]) == (6, 2, 0)
    assert row["answered"] == row["requests"] == 8 and summary["inconsistent_runs"] == 0
    assert outcome_group("candidate_partial_direction_error") == "partial"
    assert percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 0.9) == 9

    page = render_html(summary, "T <x>")
    assert "&lt;b&gt;m&amp;1&lt;/b&gt;" in page and "<b>m&1</b>" not in page
    assert page.count("<table>") == 3 and '<th scope="col">Model</th>' in page
    assert "not a verdict" in page
    markdown = render_markdown(summary)
    assert "| Model | Lang |" in markdown

    with pytest.raises(ValueError):
        summarize_benchmark(report, {"results": []})


def test_cli_report_writes_html_and_markdown(tmp_path, capsys):
    report = LLMBenchmarkRunner(lambda m: ScriptedLLM(m, {})).run(
        get_task_set("bilingual_reasoning@2"), ["m"], languages=["en"], repeats=1)
    source = tmp_path / "r.json"
    source.write_text(json.dumps(report), encoding="utf-8")
    assert llm_benchmark_cli.main(["report", str(source)]) == 0
    assert capsys.readouterr().out.split() == [str(tmp_path / "r.html"), str(tmp_path / "r.md")]
    assert "<table>" in (tmp_path / "r.html").read_text(encoding="utf-8")


def test_merge_reports():
    from ai_platform.backend.service_layer.macro.llm_benchmark.benchmark_runner import (  # pylint: disable=import-outside-toplevel
        merge_reports,
    )
    runner = LLMBenchmarkRunner(lambda m: ScriptedLLM(m, {}))
    task_set = get_task_set("bilingual_reasoning@2")
    a = runner.run(task_set, ["a"], languages=["pl"], repeats=1)
    b = runner.run(task_set, ["b"], languages=["pl"], repeats=1)
    merged = merge_reports([a, b])
    assert merged["models"] == ["a", "b"] and len(merged["results"]) == 8
    assert merged["summary"]["b [PL]"]["expected_executions"] == 4
    with pytest.raises(ValueError, match="more than one"):
        merge_reports([a, a])
    with pytest.raises(ValueError, match="repeats"):
        merge_reports([a, runner.run(task_set, ["c"], languages=["pl"], repeats=2)])


def test_review_round_trip_through_spreadsheet(tmp_path):
    from ai_platform.backend.service_layer.macro.llm_benchmark.review_service import (  # pylint: disable=import-outside-toplevel
        ReviewError,
        apply_reviews,
        review_items,
    )
    from ai_platform.backend.ui_layer.cli.review_workbook import (  # pylint: disable=import-outside-toplevel
        read_review_workbook,
        write_review_workbook,
    )
    answers = {"17": "17 * 23 = 391", "112": "Nie wiem.", "Mruczek": "Tak, Mruczek jest ssakiem.",
               "USD/PLN": "To zależy."}
    report = LLMBenchmarkRunner(lambda m: ScriptedLLM(m, answers)).run(
        get_task_set("bilingual_reasoning@2"), ["m"], languages=["pl"], repeats=1)
    screening = screen_benchmark_report(report)
    items = review_items(report, screening, sample_decided=1, seed=1)
    statuses = [i["automatic_status"] for i in items]
    assert statuses.count("manual_review") == 2 and len(items) == 3
    everything = review_items(report, screening, include_all=True)
    assert [i["index"] for i in everything] == list(range(4))
    assert {i["automatic_verdict"] for i in everything} == {"correct", "manual_review"}

    path = tmp_path / "review.xlsx"
    write_review_workbook(items, str(path))
    rows = read_review_workbook(str(path))
    assert [r["key"] for r in rows] == [i["key"] for i in items]
    verdicts = {"manual_review": "incorrect"}
    for row in rows:
        row["verdict"] = verdicts.get(row["automatic_status"], "correct")

    reviewed = apply_reviews(screening, rows, reviewer="t")
    summary = reviewed["human_review"]
    assert summary["applied"] == 3 and summary["agreement"]["agreement_rate"] == 1.0
    assert summary["agreement"]["manual_review_resolved"] == 2
    statuses = [r["automatic_assessment"]["answer_screening"]["status"]
                for r in reviewed["results"]]
    assert statuses.count("human_incorrect") == 2
    # summaries count human verdicts in the right groups
    from ai_platform.backend.service_layer.macro.llm_benchmark.benchmark_summary import (  # pylint: disable=import-outside-toplevel
        summarize_benchmark,
    )
    row = summarize_benchmark(report, reviewed)["models"][0]
    assert row["incorrect"] == 2 and row["manual_review"] == 0

    rows[0]["key"] = "other|run"
    with pytest.raises(ReviewError, match="does not match"):
        apply_reviews(screening, rows)
    rows[0]["key"], rows[0]["verdict"] = items[0]["key"], "maybe"
    with pytest.raises(ReviewError, match="verdict"):
        apply_reviews(screening, rows)


def test_cli_review_export_and_import(tmp_path):
    report = LLMBenchmarkRunner(lambda m: ScriptedLLM(m, {})).run(
        get_task_set("bilingual_reasoning@2"), ["m"], languages=["en"], repeats=1)
    source = tmp_path / "r.json"
    source.write_text(json.dumps(report), encoding="utf-8")
    assert llm_benchmark_cli.main(["review-export", str(source)]) == 1  # no screening yet
    assert llm_benchmark_cli.main(["screen", str(source)]) == 0
    assert llm_benchmark_cli.main(["review-export", str(source)]) == 0
    workbook = tmp_path / "r_review.xlsx"
    assert workbook.exists()
    assert llm_benchmark_cli.main(["review-import", str(source), str(workbook)]) == 0
    reviewed = json.loads((tmp_path / "r_screening_reviewed.json").read_text(encoding="utf-8"))
    assert reviewed["human_review"]["applied"] == 0  # nothing filled in


def test_rejected_phrases_and_old_report_enrichment():
    from ai_platform.common.evaluation import answer_screening as s  # pylint: disable=import-outside-toplevel
    assert s.check_phrase("Stolicą jest Sydney.", "Canberra", ["Sydney"])[0] == "candidate_incorrect"
    assert s.check_phrase("Nie Sydney, lecz Canberra.", "Canberra", ["Sydney"])[0] == "manual_review"
    assert s.check_phrase("Nie wiem.", "Canberra", ["Sydney"])[0] == "manual_review"
    old = {"task_set": "bilingual_reasoning", "task_set_version": "3", "results": [
        {"model": "m", "test_id": "capital_city", "language": "pl", "run_index": 0,
         "checker": "phrase", "expected": "Canberra|Canberze|Canberry", "status": "PASS",
         "answer": "Australijska stolica jest Sydney.", "finish_reason": "stop"}]}
    row = screen_benchmark_report(old)["results"][0]
    assert row["automatic_assessment"]["answer_screening"]["status"] == "candidate_incorrect"


def test_llm_judge_resumable_and_agreement(tmp_path):
    from ai_platform.backend.service_layer.macro.llm_benchmark.llm_judge_service import (  # pylint: disable=import-outside-toplevel
        judge_agreement,
        judge_report,
        judgement_columns,
        parse_judgement,
    )
    from ai_platform.backend.service_layer.macro.llm_benchmark.review_service import (  # pylint: disable=import-outside-toplevel
        apply_reviews,
        review_items,
    )
    from ai_platform.backend.ui_layer.cli.review_workbook import (  # pylint: disable=import-outside-toplevel
        read_review_workbook,
        write_review_workbook,
    )
    assert parse_judgement('ok {"result": "Correct", "reasoning": "none", "reason": "391"}') \
        == {"result": "correct", "reasoning": "none", "reason": "391"}
    assert parse_judgement('{"verdict": "partial", "reason": "x"}')["reasoning"] == "incorrect"
    assert parse_judgement("no json")["result"] is None

    class Judge:
        """Says correct when the answer contains the expected text."""
        calls = 0

        def chat_completion(self, messages, **_):
            """Judge by substring."""
            Judge.calls += 1
            prompt = messages[0]["content"]
            expected = prompt.split("EXPECTED:\n")[1].split("\n")[0]
            answer = prompt.split("ANSWER:\n")[1]
            verdict = "correct" if expected.split("|")[0] in answer else "incorrect"
            return ChatResult(text=json.dumps({"result": verdict, "reasoning": "none",
                                               "reason": "r"}), model="j")

    answers = {"17": "17 * 23 = 391", "Mruczek": "Nie wiem."}
    report = LLMBenchmarkRunner(lambda m: ScriptedLLM(m, answers)).run(
        get_task_set("bilingual_reasoning@2"), ["m"], languages=["pl"], repeats=1)
    saved = []
    data = judge_report(report, Judge(), "fake:judge", workers=2, save=saved.append,
                        batched=False)
    assert len(data["judgements"]) == 4 and saved
    calls = Judge.calls
    judge_report(report, Judge(), "fake:judge", existing=data, batched=False)  # resume
    assert Judge.calls == calls
    with pytest.raises(ValueError):
        judge_report(report, Judge(), "other:judge", existing=data)

    screening = screen_benchmark_report(report)
    items = review_items(report, screening, include_all=True)
    judgement_columns(data, items)
    path = tmp_path / "r.xlsx"
    write_review_workbook(items, str(path))
    from openpyxl import load_workbook  # pylint: disable=import-outside-toplevel
    headers = [c.value for c in load_workbook(path).active[1]]
    assert headers.index("Rule verdict") + 1 == headers.index("LLM result") \
        == headers.index("LLM reasoning") - 1 == headers.index("Human result") - 2 \
        == headers.index("Human reasoning") - 3
    rows = read_review_workbook(str(path))
    assert rows[0]["llm_result"] in ("correct", "incorrect")
    for row in rows:
        row["verdict"] = row["llm_result"]
    agreement = judge_agreement(data, apply_reviews(screening, rows))
    assert agreement["agreement_rate"] == 1.0 and agreement["compared"] == 4


def test_llm_judge_batched_one_prompt_per_question():
    from ai_platform.backend.service_layer.macro.llm_benchmark.llm_judge_service import (  # pylint: disable=import-outside-toplevel
        estimate,
        judge_report,
        select_records,
    )

    class BatchJudge:
        """Answers a batch prompt; skips the last id once to test the retry."""
        prompts = []

        def chat_completion(self, messages, **_):
            """Return a JSON array for all ids but (first time) the last."""
            prompt = messages[0]["content"]
            BatchJudge.prompts.append(prompt)
            ids = [line.split("id: ")[1].split(" ")[0] for line in prompt.splitlines()
                   if line.startswith("--- id: ")]
            if len(BatchJudge.prompts) == 1:
                ids = ids[:-1]
            return ChatResult(text=json.dumps([{"id": i, "result": "correct",
                                                "reasoning": "none", "reason": "ok"}
                                               for i in ids]), model="j")

    report = LLMBenchmarkRunner(lambda m: ScriptedLLM(m, {"17": "391"})).run(
        get_task_set("bilingual_reasoning@2"), ["a", "b"], languages=["pl", "en"], repeats=2)
    assert estimate(report["results"])["prompts"] == 8  # 4 tasks x 2 languages
    data = judge_report(report, BatchJudge(), "fake:j", workers=1)
    assert len(BatchJudge.prompts) == 8
    assert sum(j["result"] is None for j in data["judgements"].values()) == 1
    judge_report(report, BatchJudge(), "fake:j", existing=data, workers=1)  # retries the miss
    assert len(BatchJudge.prompts) == 9
    assert all(j["result"] == "correct" for j in data["judgements"].values())
    screening = screen_benchmark_report(report)
    undecided = select_records(report, screening, {}, "undecided")
    assert all(screening["results"][report["results"].index(r)]["automatic_assessment"]
               ["answer_screening"]["status"] == "manual_review" for r in undecided)


def test_llm_judge_stops_when_every_call_fails_and_files_per_judge(tmp_path):
    from ai_platform.backend.service_layer.macro.llm_benchmark.llm_judge_service import (  # pylint: disable=import-outside-toplevel
        judge_report,
        judgement_counts,
    )
    from ai_platform.backend.ui_layer.cli.llm_benchmark_cli import judge_path  # pylint: disable=import-outside-toplevel
    from ai_platform.common.llm.llm_exception import LLMRequestError  # pylint: disable=import-outside-toplevel

    class QuotaJudge:
        """Every call fails like an exhausted free-tier quota."""
        calls = 0

        def chat_completion(self, *_, **__):
            """Raise HTTP 429."""
            QuotaJudge.calls += 1
            raise LLMRequestError("HTTP 429 quota exceeded", 429)

    report = LLMBenchmarkRunner(lambda m: ScriptedLLM(m, {"17": "391"})).run(
        get_task_set("bilingual_reasoning@2"), ["a"], languages=["pl", "en"], repeats=1)
    data = judge_report(report, QuotaJudge(), "fake:j", workers=2, retries=0)
    assert QuotaJudge.calls == 2  # first round only, not all 8 prompts
    assert judgement_counts(data) == {"pending": 2}
    assert judgement_counts(data, report) == {"pending": 8}
    source = tmp_path / "r.json"
    assert judge_path(source, "google:gemini-3.5-flash").name == \
        "r_judge_google-gemini-3.5-flash.json"
    assert judge_path(source, "openai-compatible:openai/gpt-oss-120b").name == \
        "r_judge_openai-compatible-openai-gpt-oss-120b.json"
    assert judge_path(source).name == "r_judge.json"


def test_llm_judge_retries_transient_errors():
    from ai_platform.backend.service_layer.macro.llm_benchmark.llm_judge_service import (  # pylint: disable=import-outside-toplevel
        judge_batch,
    )
    from ai_platform.common.llm.llm_exception import LLMRequestError  # pylint: disable=import-outside-toplevel

    class BusyJudge:
        """503 twice ("high demand"), then a proper reply."""
        calls = 0

        def chat_completion(self, *_, **__):
            """Fail twice, then answer."""
            BusyJudge.calls += 1
            if BusyJudge.calls <= 2:
                raise LLMRequestError("HTTP 503 high demand", 503)
            return ChatResult(text='[{"id": "A1", "result": "correct", "reasoning": "none"}]',
                              model="j")

    waits = []
    records = [{"prompt": "q", "expected": "e", "answer": "a", "status": "PASS"}]
    assert judge_batch(BusyJudge(), records, sleep=waits.append)[0]["result"] == "correct"
    assert waits == [20.0, 60.0]
    BusyJudge.calls = 0
    failed = judge_batch(BusyJudge(), records, retries=1, sleep=waits.append)
    assert failed[0]["result"] is None and "503" in failed[0]["reason"]


def test_openai_compatible_base_url_with_prefix_and_user_agent():
    from ai_platform.common.llm.openai_compatible_adapter import OpenAICompatibleAdapter  # pylint: disable=import-outside-toplevel
    from ai_platform.common.util.http_json_client import (  # pylint: disable=import-outside-toplevel
        DEFAULT_USER_AGENT,
    )

    adapter = OpenAICompatibleAdapter()
    adapter.initialize({"base_url": "https://api.example.com/openai/v1/", "model": "m"})
    assert adapter.base_url == "https://api.example.com/openai"
    with FakeJsonServer({("POST", "/v1/chat/completions"): openai_chat_answer("hi")}) as server:
        adapter.initialize({"base_url": server.url + "/v1", "model": "m"})
        assert adapter.chat_completion([{"role": "user", "content": "x"}]).text == "hi"
        assert server.requests[-1]["headers"].get("user-agent") == DEFAULT_USER_AGENT


def test_llm_judge_splits_too_large_batches_and_skips_daily_quota_retries():
    from ai_platform.backend.service_layer.macro.llm_benchmark.llm_judge_service import (  # pylint: disable=import-outside-toplevel
        judge_batch,
    )
    from ai_platform.common.llm.llm_exception import LLMRequestError  # pylint: disable=import-outside-toplevel

    class SmallLimitJudge:
        """HTTP 413 for prompts with more than two answers."""
        sizes = []

        def chat_completion(self, messages, **_):
            """Answer every id, or refuse a batch that is too large."""
            ids = [line.split("id: ")[1].split(" ")[0] for line in
                   messages[0]["content"].splitlines() if line.startswith("--- id: ")]
            SmallLimitJudge.sizes.append(len(ids))
            if len(ids) > 2:
                raise LLMRequestError("HTTP 413 Request too large ... tokens per minute", 413)
            return ChatResult(text=json.dumps([{"id": i, "result": "correct",
                                                "reasoning": "none", "reason": "ok"}
                                               for i in ids]), model="j")

    records = [{"prompt": "q", "expected": "e", "answer": f"a{n}", "status": "PASS"}
               for n in range(5)]
    result = judge_batch(SmallLimitJudge(), records, sleep=lambda s: None)
    assert [r["result"] for r in result] == ["correct"] * 5
    assert SmallLimitJudge.sizes == [5, 2, 3, 1, 2]

    class DailyQuotaJudge:
        """429 with a per-day quota message."""

        def chat_completion(self, *_, **__):
            """Always over the daily quota."""
            raise LLMRequestError("HTTP 429 Generate content requests per day limit exceeded", 429)

    waits = []
    assert judge_batch(DailyQuotaJudge(), records[:1], sleep=waits.append)[0]["result"] is None
    assert not waits


def test_llm_judge_schema1_migrates_locally_and_human_reasoning():
    from ai_platform.backend.service_layer.macro.llm_benchmark.llm_judge_service import (  # pylint: disable=import-outside-toplevel
        JUDGE_SCHEMA,
        judge_agreement,
        migrate_judgements,
    )
    from ai_platform.backend.service_layer.macro.llm_benchmark.review_service import (  # pylint: disable=import-outside-toplevel
        apply_reviews,
        review_items,
    )

    report = LLMBenchmarkRunner(lambda m: ScriptedLLM(m, {"17": "391"})).run(
        get_task_set("bilingual_reasoning@2"), ["a"], languages=["en"], repeats=1)
    keys = [r["key"] for r in review_items(report, screen_benchmark_report(report),
                                           include_all=True)]
    old = {"schema": "ai_platform.llm_judge/1", "judge": "x", "judgements": {
        keys[0]: {"verdict": "partial", "reason": "wrong step"},
        keys[1]: {"verdict": "unclear", "reason": "Tekst jest niespójny i zapętlony."},
        keys[2]: {"verdict": "unclear", "reason": "The text is cut off before any answer."},
        keys[3]: {"verdict": "incorrect", "reason": "wrong"}}}
    new = migrate_judgements(old, report)
    table = new["judgements"]
    assert new["schema"] == JUDGE_SCHEMA and new["migrated_from"] == "ai_platform.llm_judge/1"
    assert (table[keys[0]]["result"], table[keys[0]]["reasoning"]) == ("correct", "incorrect")
    assert table[keys[1]]["result"] == "incorrect"
    assert table[keys[2]]["result"] == "unclear"
    assert table[keys[3]]["reasoning"] == "not_assessed"
    assert table[keys[0]]["legacy_verdict"] == "partial"
    screening = screen_benchmark_report(report)
    reviews = [{"index": 0, "key": keys[0], "verdict": "correct", "human_reasoning": "incorrect"},
               {"index": 3, "key": keys[3], "verdict": "", "human_reasoning": "none"}]
    reviewed = apply_reviews(screening, reviews)
    rows = reviewed["results"]
    assert rows[0]["automatic_assessment"]["answer_screening"]["human_reasoning"] == "incorrect"
    assert "human_verdict" not in rows[3]["automatic_assessment"]["answer_screening"]
    agreement = judge_agreement(old, reviewed)
    assert agreement["agreed"] == 1
    assert agreement["reasoning"]["agreed"] == 1  # not_assessed record left out


def test_llm_judge_retries_connection_errors():
    from ai_platform.backend.service_layer.macro.llm_benchmark.llm_judge_service import (  # pylint: disable=import-outside-toplevel
        judge_batch,
    )

    class SlowJudge:
        """Read timeout once, then a reply."""
        calls = 0

        def chat_completion(self, *_, **__):
            """Time out first."""
            SlowJudge.calls += 1
            if SlowJudge.calls == 1:
                raise LLMConnectionError("The read operation timed out")
            return ChatResult(text='[{"id": "A1", "result": "correct", "reasoning": "none"}]',
                              model="j")

    waits = []
    records = [{"prompt": "q", "expected": "e", "answer": "a", "status": "PASS"}]
    assert judge_batch(SlowJudge(), records, sleep=waits.append)[0]["result"] == "correct"
    assert waits == [20.0]
