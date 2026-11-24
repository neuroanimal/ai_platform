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
    python -m ai_platform.backend.ui_layer.cli.llm_benchmark_cli judge results/r.json \\
        --provider google --model <model id>   # -> results/r_judge_google-<model id>.json
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
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ai_platform.backend.service_layer.macro.llm_benchmark.task_set_service import (
    get_task_set,
    list_task_sets,
)
from ai_platform.backend.service_layer.macro.llm_benchmark.llm_judge_service import (
    estimate,
    judge_agreement,
    judge_report,
    judgement_columns,
    judgement_counts,
    select_records,
)
from ai_platform.common.llm.bedrock_adapter import BedrockAdapter
from ai_platform.common.llm.google_adapter import GoogleAdapter
from ai_platform.common.llm.llm_exception import LLMError
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
#: Judges: remote providers recommended (a strong model), local ones work too.
JUDGE_PROVIDERS = {"anthropic": AnthropicAdapter, "openai": OpenAIAdapter,
                   "google": GoogleAdapter, "bedrock": BedrockAdapter,
                   "openai-compatible": OpenAICompatibleAdapter, "ollama": OllamaAdapter}
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
    items = review_items(report, screening, sample_decided=args.sample_decided, seed=args.seed,
                         include_all=args.all)
    if args.judge:
        judgements_file = Path(args.judge)
    else:
        found = sorted(source.parent.glob(source.stem + "_judge*.json"))
        if len(found) > 1:
            print("several judgement files, choose one with --judge: "
                  + ", ".join(f.name for f in found), file=sys.stderr)
            return 1
        judgements_file = found[0] if found else judge_path(source)
    if judgements_file.exists():
        judgement_columns(json.loads(judgements_file.read_text(encoding="utf-8")), items)
    if args.carry_over:
        previous = {row["key"]: row for row in read_review_workbook(args.carry_over)}
        for item in items:
            old = previous.get(item["key"]) or {}
            item["verdict"] = old.get("verdict") or ""
            item["human_reasoning"] = old.get("human_reasoning") or ""
            item["comment"] = old.get("comment") or ""
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


def judge_path(report_path: Path, judge_name: Optional[str] = None) -> Path:
    """<report>_judge_<judge>.json next to the report (<report>_judge.json without a name).

    One file per judge, so several judges can be run on the same report.
    """
    if not judge_name:
        return report_path.with_name(report_path.stem + "_judge.json")
    slug = re.sub(r"[^A-Za-z0-9.]+", "-", judge_name).strip("-")
    return report_path.with_name(f"{report_path.stem}_judge_{slug}.json")


def command_judge(args) -> int:  # pylint: disable=too-many-locals
    """Ask a (remote) LLM for a verdict on every answer; resumable."""
    source = Path(args.input)
    report = json.loads(source.read_text(encoding="utf-8"))
    judge_name = f"{args.provider}:{args.model}" if args.provider and args.model else None
    target = Path(args.output) if args.output else judge_path(source, judge_name)
    existing = json.loads(target.read_text(encoding="utf-8")) if target.exists() else None
    screening_file = screening_path(source)
    screening = json.loads(screening_file.read_text(encoding="utf-8")) \
        if screening_file.exists() else None
    if args.estimate:
        done = (existing or {}).get("judgements", {})
        try:
            todo = select_records(report, screening, done, args.scope)
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 1
        print(json.dumps(estimate(todo, batched=not args.one_per_prompt), indent=2))
        return 0
    if not args.provider or not args.model:
        print("--provider and --model are required (or use --estimate)", file=sys.stderr)
        return 1
    judge = JUDGE_PROVIDERS[args.provider]()
    config = {"model": args.model, "temperature": 0, "max_tokens": 200,
              "timeout": args.timeout}
    if args.base_url:
        config["base_url"] = args.base_url
    if args.api_key_env:
        config["api_key_env"] = args.api_key_env
    try:
        judge.initialize(config)
        data = judge_report(report, judge, judge_name, existing=existing,
                            workers=args.workers, screening=screening, scope=args.scope,
                            batched=not args.one_per_prompt, pause=args.pause,
                            retries=args.retries, reserve=args.thinking_reserve,
                            progress=lambda m: print(m, file=sys.stderr),
                            save=lambda d: write_json(d, target))
    except (LLMError, ValueError) as exc:
        print(f"cannot judge: {exc}", file=sys.stderr)
        return 1
    print(write_json(data, target))
    counts = judgement_counts(data, report)
    print(f"result: {json.dumps(counts)}", file=sys.stderr)
    print(f"reasoning: {json.dumps(judgement_counts(data, report, 'reasoning'))}",
          file=sys.stderr)
    if counts.get("pending"):
        print(f"{counts['pending']} not judged (errors); run the same command again to retry them",
              file=sys.stderr)
    reviewed = source.with_name(source.stem + "_screening_reviewed.json")
    if reviewed.exists():
        agreement = judge_agreement(data, json.loads(reviewed.read_text(encoding="utf-8")))
        print(f"agreement with human verdicts: {json.dumps(agreement)}", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:  # pylint: disable=too-many-statements
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
    export.add_argument("--all", action="store_true", help="every record (complete sheet)")
    export.add_argument("--judge", default=None,
                        help="judgement file (default <report>_judge.json if present)")
    export.add_argument("--carry-over", default=None,
                        help="earlier filled-in sheet whose human verdicts are copied over")

    judge = sub.add_parser("judge", help="LLM-as-judge verdict for every answer (resumable)")
    judge.add_argument("input")
    judge.add_argument("--provider", choices=sorted(JUDGE_PROVIDERS))
    judge.add_argument("--model")
    judge.add_argument("--base-url", default=None)
    judge.add_argument("--api-key-env", default=None)
    judge.add_argument("--workers", type=int, default=4)
    judge.add_argument("--timeout", type=float, default=300.0,
                       help="seconds per prompt; a batch of 22 answers to a thinking model "
                            "can take over two minutes")
    judge.add_argument("--retries", type=int, default=3,
                       help="retries of a prompt on HTTP 429/5xx, after 20, 60, 120 s")
    judge.add_argument("--thinking-reserve", type=int, default=2000,
                       help="output tokens added per prompt for the judge's hidden reasoning")
    judge.add_argument("--pause", type=float, default=0.0,
                       help="seconds between rounds of --workers prompts (free-tier rate limits)")
    judge.add_argument("--scope", choices=["all", "undecided"], default="all",
                       help="'undecided' = only records the rules sent to manual review")
    judge.add_argument("--one-per-prompt", action="store_true",
                       help="one answer per prompt instead of all answers to a question")
    judge.add_argument("--estimate", action="store_true",
                       help="print prompts and approximate tokens, send nothing")
    judge.add_argument("--output", default=None)
    judge.set_defaults(func=command_judge)
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
