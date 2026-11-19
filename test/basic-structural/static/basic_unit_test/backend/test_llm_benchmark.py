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
    task_set = get_task_set("bilingual_reasoning")
    assert task_set is get_task_set("bilingual_reasoning@2")
    assert task_set.languages == ["pl", "en"]
    assert {t.checker for t in task_set.tasks} == {
        "multiplication", "percentage", "syllogism", "currency_vs_cpi"}
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

    report = LLMBenchmarkRunner(factory).run(get_task_set("bilingual_reasoning"), ["a", "b"],
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
        get_task_set("bilingual_reasoning"), ["x"], repeats=1)
    assert report["warmup"]["x"]["status"] == "FAIL" and report["results"] == []


def test_runner_argument_validation():
    runner = LLMBenchmarkRunner(lambda m: ScriptedLLM(m, {}))
    with pytest.raises(ValueError):
        runner.run(get_task_set("bilingual_reasoning"), [], repeats=1)
    with pytest.raises(ValueError):
        runner.run(get_task_set("bilingual_reasoning"), ["m"], repeats=0)


def test_cli_run_and_screen_against_fake_server(tmp_path, capsys):
    with FakeJsonServer({("POST", "/v1/chat/completions"):
                         openai_chat_answer("17 * 23 = 391")}) as server:
        code = llm_benchmark_cli.main([
            "run", "--provider", "openai-compatible", "--base-url", server.url,
            "--models", "m", "--languages", "en", "--repeats", "1",
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
        get_task_set("bilingual_reasoning"), ["<b>m&1</b>"], languages=["pl"], repeats=2,
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
        get_task_set("bilingual_reasoning"), ["m"], languages=["en"], repeats=1)
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
    task_set = get_task_set("bilingual_reasoning")
    a = runner.run(task_set, ["a"], languages=["pl"], repeats=1)
    b = runner.run(task_set, ["b"], languages=["pl"], repeats=1)
    merged = merge_reports([a, b])
    assert merged["models"] == ["a", "b"] and len(merged["results"]) == 8
    assert merged["summary"]["b [PL]"]["expected_executions"] == 4
    with pytest.raises(ValueError, match="more than one"):
        merge_reports([a, a])
    with pytest.raises(ValueError, match="repeats"):
        merge_reports([a, runner.run(task_set, ["c"], languages=["pl"], repeats=2)])
