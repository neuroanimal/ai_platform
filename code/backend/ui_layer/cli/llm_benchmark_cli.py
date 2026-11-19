"""
Command line for the LLM benchmark (integrates config/test_env tests 28-30).

    python -m ai_platform.backend.ui_layer.cli.llm_benchmark_cli list
    python -m ai_platform.backend.ui_layer.cli.llm_benchmark_cli run \\
        --provider localai --base-url http://127.0.0.1:8081 \\
        --models qwen25-05b-localai bielik-15b-localai --repeats 3 --screen
    python -m ai_platform.backend.ui_layer.cli.llm_benchmark_cli screen results/report.json
    python -m ai_platform.backend.ui_layer.cli.llm_benchmark_cli report results/report.json
    python -m ai_platform.backend.ui_layer.cli.llm_benchmark_cli merge a.json b.json \\
        --output ab.json
    python -m ai_platform.backend.ui_layer.cli.llm_benchmark_cli review-export results/r.json \\
        --sample-decided 20                 # -> results/r_review.xlsx
    python -m ai_platform.backend.ui_layer.cli.llm_benchmark_cli review-import results/r.json \\
        results/r_review.xlsx --reviewer greg  # -> results/r_screening_reviewed.json
    python -m ai_platform.backend.ui_layer.cli.llm_benchmark_cli report results/r.json \\
        --screening results/r_screening_reviewed.json

Former test_env scripts as commands:

    test_30_bilingual_quality_v3.py   run (defaults)
    test_29_bielik_quality.py         run --languages pl --models qwen25-05b-localai
                                          qwen25-15b-localai bielik-15b-localai --repeats 1
    test_28_quality.py                run --languages pl --models qwen25-05b-localai
                                          qwen25-15b-localai --repeats 1
    test_30a_analysis_v4_2.py         screen <report>
    (new)                             report <report>  -> <report>.html + <report>.md tables

Writes JSON files only where told (``--output``, default ``./results``);
prints progress to stderr and the written paths to stdout. Exit status 1
when no request produced an answer.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ai_platform.backend.service_layer.macro.llm_benchmark.task_set_service import (
    get_task_set,
    list_task_sets,
)
from ai_platform.backend.service_layer.macro.llm_benchmark.review_service import (
    ReviewError,
    apply_reviews,
    review_items,
)
from ai_platform.backend.ui_layer.cli.review_workbook import (
    read_review_workbook,
    write_review_workbook,
)
from ai_platform.backend.service_layer.macro.llm_benchmark.benchmark_summary import (
    summarize_benchmark,
)
from ai_platform.backend.ui_layer.cli.benchmark_report_rendering import (
    render_html,
    render_markdown,
)
from ai_platform.backend.service_layer.macro.llm_benchmark.benchmark_runner import (
    LLMBenchmarkRunner,
    merge_reports,
)
from ai_platform.backend.service_layer.macro.llm_benchmark.screening_service import (
    screen_benchmark_report,
)
from ai_platform.common.llm.anthropic_adapter import AnthropicAdapter
from ai_platform.common.llm.localai_adapter import LocalAIAdapter
from ai_platform.common.llm.ollama_adapter import OllamaAdapter
from ai_platform.common.llm.openai_adapter import OpenAIAdapter
from ai_platform.common.llm.openai_compatible_adapter import OpenAICompatibleAdapter

PROVIDERS = {
    "localai": LocalAIAdapter,
    "ollama": OllamaAdapter,
    "openai-compatible": OpenAICompatibleAdapter,
    "openai": OpenAIAdapter,
    "anthropic": AnthropicAdapter,
}
DEFAULT_MODELS = ["qwen25-05b-localai", "qwen25-15b-localai", "bielik-15b-localai"]


def write_json(data: Dict, path: Path) -> Path:
    """Write ``data`` as UTF-8 JSON, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path.resolve()


def screening_path(report_path: Path) -> Path:
    """<report>_screening.json next to the report."""
    return report_path.with_name(report_path.stem + "_screening.json")


def command_list(_args) -> int:
    """Print task sets and providers."""
    for name in list_task_sets():
        task_set = get_task_set(name)
        print(f"task set  {name:28} {len(task_set.tasks)} tasks, languages {task_set.languages}")
    for name in PROVIDERS:
        print(f"provider  {name}")
    return 0


def command_run(args) -> int:
    """Run the benchmark (and optionally screen it)."""
    task_set = get_task_set(args.task_set)

    def factory(model: str):
        llm = PROVIDERS[args.provider]()
        config = {"model": model, "temperature": args.temperature,
                  "max_tokens": args.max_tokens, "timeout": args.timeout}
        if args.base_url:
            config["base_url"] = args.base_url
        if args.api_key_env:
            config["api_key_env"] = args.api_key_env
        llm.initialize(config)
        return llm

    runner = LLMBenchmarkRunner(factory, progress=lambda m: print(m, file=sys.stderr))
    report = runner.run(task_set, args.models, languages=args.languages, repeats=args.repeats,
                        warmup=not args.no_warmup,
                        metadata={"provider": args.provider, "endpoint": args.base_url,
                                  "temperature": args.temperature,
                                  "max_tokens": args.max_tokens})
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = Path(args.output) if args.output else \
        Path("results") / f"llm_benchmark_{task_set.name}_{stamp}.json"
    print(write_json(report, output))
    if args.screen:
        print(write_json(screen_benchmark_report(report, source=str(output)),
                         screening_path(output)))
    return 0 if any(r["status"] == "PASS" for r in report["results"]) else 1


def command_screen(args) -> int:
    """Screen an existing report."""
    source = Path(args.input)
    report = json.loads(source.read_text(encoding="utf-8"))
    output = Path(args.output) if args.output else screening_path(source)
    print(write_json(screen_benchmark_report(report, source=str(source.resolve())), output))
    return 0


def command_report(args) -> int:
    """Write HTML and Markdown comparison tables for a report."""
    source = Path(args.input)
    report = json.loads(source.read_text(encoding="utf-8"))
    screening_file = Path(args.screening) if args.screening else screening_path(source)
    if screening_file.exists():
        screening = json.loads(screening_file.read_text(encoding="utf-8"))
    else:
        screening = screen_benchmark_report(report, source=str(source.resolve()))
    summary = summarize_benchmark(report, screening)
    title = args.title or f"LLM benchmark - {source.stem}"
    for extension, render in ((".html", render_html), (".md", render_markdown)):
        target = source.with_suffix(extension) if not args.output_stem else \
            Path(args.output_stem + extension)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render(summary, title), encoding="utf-8")
        print(target.resolve())
    return 0


def command_merge(args) -> int:
    """Merge comparable reports into one file."""
    reports = [json.loads(Path(p).read_text(encoding="utf-8")) for p in args.inputs]
    try:
        merged = merge_reports(reports)
    except ValueError as exc:
        print(f"cannot merge: {exc}", file=sys.stderr)
        return 1
    merged["merged_files"] = [str(Path(p).resolve()) for p in args.inputs]
    print(write_json(merged, Path(args.output)))
    return 0


def _load_report_and_screening(args):
    source = Path(args.input)
    report = json.loads(source.read_text(encoding="utf-8"))
    screening_file = Path(args.screening) if args.screening else screening_path(source)
    if not screening_file.exists():
        raise ReviewError(f"no screening at {screening_file}; run 'screen' first")
    return source, report, json.loads(screening_file.read_text(encoding="utf-8"))


def command_review_export(args) -> int:
    """Write the review spreadsheet (manual_review items + a decided sample)."""
    try:
        source, report, screening = _load_report_and_screening(args)
    except ReviewError as exc:
        print(exc, file=sys.stderr)
        return 1
    items = review_items(report, screening, sample_decided=args.sample_decided, seed=args.seed)
    target = Path(args.output) if args.output else source.with_name(source.stem + "_review.xlsx")
    write_review_workbook(items, str(target))
    print(target.resolve())
    print(f"{len(items)} items ({sum(i['automatic_status'] == 'manual_review' for i in items)} "
          "manual review)", file=sys.stderr)
    return 0


def command_review_import(args) -> int:
    """Apply a filled-in review spreadsheet to the screening."""
    try:
        source, _, screening = _load_report_and_screening(args)
        reviewed = apply_reviews(screening, read_review_workbook(args.workbook),
                                 reviewer=args.reviewer)
    except ReviewError as exc:
        print(f"cannot import: {exc}", file=sys.stderr)
        return 1
    target = Path(args.output) if args.output else \
        source.with_name(source.stem + "_screening_reviewed.json")
    print(write_json(reviewed, target))
    print(json.dumps(reviewed["human_review"], indent=2), file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Argument parser with list / run / screen subcommands."""
    parser = argparse.ArgumentParser(prog="llm_benchmark", description=__doc__.splitlines()[1])
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="list task sets and providers").set_defaults(func=command_list)

    run = sub.add_parser("run", help="run a task set against models")
    run.add_argument("--provider", choices=sorted(PROVIDERS), default="localai")
    run.add_argument("--base-url", default="http://127.0.0.1:8081")
    run.add_argument("--api-key-env", default=None)
    run.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    run.add_argument("--task-set", default="bilingual_reasoning")
    run.add_argument("--languages", nargs="+", default=None)
    run.add_argument("--repeats", type=int, default=3)
    # 768: at 384 verbose models (Bielik 11B in Polish: 9 of 12 answers) were cut
    # off before their conclusion, measuring the limit rather than the model.
    run.add_argument("--max-tokens", type=int, default=768)
    run.add_argument("--temperature", type=float, default=0.0)
    run.add_argument("--timeout", type=float, default=300.0)
    run.add_argument("--no-warmup", action="store_true")
    run.add_argument("--output", default=None)
    run.add_argument("--screen", action="store_true", help="also write the screening")
    run.set_defaults(func=command_run)

    screen = sub.add_parser("screen", help="screen an existing report")
    screen.add_argument("input")
    screen.add_argument("--output", default=None)
    screen.set_defaults(func=command_screen)

    report = sub.add_parser("report", help="HTML + Markdown comparison tables for a report")
    report.add_argument("input")
    report.add_argument("--screening", default=None,
                        help="screening file (default <report>_screening.json, else computed)")
    report.add_argument("--output-stem", default=None, help="path without extension")
    report.add_argument("--title", default=None)
    report.set_defaults(func=command_report)

    merge = sub.add_parser("merge", help="merge reports of comparable runs")
    merge.add_argument("inputs", nargs="+")
    merge.add_argument("--output", required=True)
    merge.set_defaults(func=command_merge)

    export = sub.add_parser("review-export", help="spreadsheet for human review")
    export.add_argument("input")
    export.add_argument("--screening", default=None)
    export.add_argument("--sample-decided", type=int, default=0,
                        help="also include N random records the rules decided")
    export.add_argument("--seed", type=int, default=0)
    export.add_argument("--output", default=None)
    export.set_defaults(func=command_review_export)

    imp = sub.add_parser("review-import", help="apply a filled-in review spreadsheet")
    imp.add_argument("input")
    imp.add_argument("workbook")
    imp.add_argument("--screening", default=None)
    imp.add_argument("--reviewer", default=None)
    imp.add_argument("--output", default=None)
    imp.set_defaults(func=command_review_import)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point."""
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
