"""
Command line for the tool-use benchmark.

    python -m ai_platform.backend.ui_layer.cli.agent_benchmark_cli \\
        --models qwen2.5:1.5b llama3.2:3b gemma3:4b --modes auto json \\
        --output results/tool_use.json          # also .html and .md

Provider is Ollama by default (``--provider localai`` for LocalAI); the
search tool indexes the bilingual_qa corpus with ``--embedder``.
"""

import argparse
import html
import json
import sys
from pathlib import Path
from typing import List, Optional

from ai_platform.backend.service_layer.macro.agent_benchmark.tool_use_evaluator import (
    evaluate_tool_use,
)
from ai_platform.backend.ui_layer.cli.benchmark_report_rendering import html_table, md_table
from ai_platform.common.llm.localai_adapter import LocalAIAdapter
from ai_platform.common.llm.ollama_adapter import OllamaAdapter
from ai_platform.common.rag.embedder import create_embedder

PROVIDERS = {"ollama": (OllamaAdapter, "http://127.0.0.1:11434"),
             "localai": (LocalAIAdapter, "http://127.0.0.1:8081")}
SUMMARY = [("model", "Model"), ("mode", "Mode"), ("tasks", "Tasks"),
           ("tool_choice_ok", "Right tools"), ("answer_correct", "Right answer"),
           ("both_ok", "Both"), ("valid_call_rate", "Valid calls"),
           ("mean_steps", "Mean steps"), ("errors", "Not answered")]
ROWS = [("model", "Model"), ("mode", "Mode"), ("task_id", "Task"), ("question", "Question"),
        ("expected_tools", "Expected tools"), ("tools_used", "Tools used"),
        ("expected", "Expected"), ("answer", "Answer"), ("screening", "Screening"),
        ("stop_reason", "Stop")]
CAVEAT = ("9 tasks per model and mode: a quick check of whether a model can drive tools, "
          "not a general agent benchmark. 'Right answer' is the rule-based screening.")


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(prog="agent_benchmark", description=__doc__.splitlines()[1])
    parser.add_argument("--provider", choices=sorted(PROVIDERS), default="ollama")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--modes", nargs="+", choices=["auto", "native", "json"],
                        default=["auto"])
    parser.add_argument("--embedder", default="ollama:bge-m3")
    parser.add_argument("--max-steps", type=int, default=5)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--title", default="Tool use: which local models can drive tools")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    adapter_cls, default_url = PROVIDERS[args.provider]

    def factory(model):
        llm = adapter_cls()
        llm.initialize({"model": model, "base_url": args.base_url or default_url,
                        "temperature": 0, "max_tokens": args.max_tokens,
                        "timeout": args.timeout})
        return llm

    report = evaluate_tool_use(args.models, factory, create_embedder(args.embedder),
                               modes=args.modes, max_steps=args.max_steps,
                               progress=lambda m: print(m, file=sys.stderr))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    rows = [{**r, "answer": " ".join(str(r["answer"] or "").split())[:200]}
            for r in report["results"]]
    title = html.escape(args.title)
    output.with_suffix(".html").write_text(
        f'<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8"><title>{title}</title>'
        "<style>body{font-family:sans-serif;margin:2rem}table{border-collapse:collapse;"
        "margin:1.5rem 0}th,td{border:1px solid #999;padding:.3rem .6rem;text-align:left;"
        "vertical-align:top}caption{text-align:left;font-weight:bold}</style></head><body>"
        f"<h1>{title}</h1><p>{CAVEAT}</p>"
        + html_table("Summary", SUMMARY, report["summary"])
        + html_table("Every run", ROWS, rows) + "</body></html>\n", encoding="utf-8")
    output.with_suffix(".md").write_text("\n".join(
        [f"# {title}", "", f"> {CAVEAT}", "", "## Summary", "",
         md_table(SUMMARY, report["summary"]), "", "## Every run", "", md_table(ROWS, rows),
         ""]), encoding="utf-8")
    for path in (output, output.with_suffix(".html"), output.with_suffix(".md")):
        print(path.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
