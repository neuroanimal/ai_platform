"""Live LLM benchmark smoke test (replaces config/test_env tests 28-30 as a test).

Runs the built-in ``bilingual_reasoning`` task set (newest version) once, in Polish, against
a local OpenAI-compatible server, and screens the answers. Skipped when the
server or model is not available. Override with:

    AI_PLATFORM_BENCH_URL     default http://127.0.0.1:8081 (LocalAI, WSL2)
    AI_PLATFORM_BENCH_MODEL   default qwen25-05b-localai

What it asserts is technical (every request answered, the report and the
screening are complete), not model quality - quality is what the report
is for.
"""

import os

import pytest

from ai_platform.backend.domain_layer.business_logic.llm_benchmark.task_sets import get_task_set
from ai_platform.backend.service_layer.macro.llm_benchmark.benchmark_runner import (
    LLMBenchmarkRunner,
)
from ai_platform.backend.service_layer.macro.llm_benchmark.screening_service import (
    screen_benchmark_report,
)
from ai_platform.common.llm.localai_adapter import LocalAIAdapter

URL = os.environ.get("AI_PLATFORM_BENCH_URL", "http://127.0.0.1:8081")
MODEL = os.environ.get("AI_PLATFORM_BENCH_MODEL", "qwen25-05b-localai")


def factory(model):
    """LocalAI adapter for ``model``."""
    llm = LocalAIAdapter()
    llm.initialize({"base_url": URL, "model": model, "temperature": 0, "max_tokens": 256,
                    "timeout": 300})
    return llm


def test_bilingual_reasoning_live():
    probe = factory(MODEL)
    if not probe.health()["model_available"]:
        pytest.skip(f"{MODEL} not served at {URL}")
    task_set = get_task_set("bilingual_reasoning")
    report = LLMBenchmarkRunner(factory).run(task_set, [MODEL], languages=["pl"], repeats=1)
    assert report["warmup"][MODEL]["status"] == "PASS"
    assert [r["status"] for r in report["results"]] == ["PASS"] * len(task_set.tasks)
    analysis = screen_benchmark_report(report)
    assert analysis["summary"]["records"] == len(task_set.tasks)
    assert all(r["automatic_assessment"]["answer_screening"]["checker"]
               for r in analysis["results"])
