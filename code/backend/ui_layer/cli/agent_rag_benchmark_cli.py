"""
Command line for the agent-with-RAG benchmark.

Plain RAG vs. agent with search vs. agent with search and calculator:

    python -m ai_platform.backend.ui_layer.cli.agent_rag_benchmark_cli \\
        --models qwen2.5:3b llama3.2:3b --output results/agent_rag.json   # also .html and .md

``--rescreen REPORT --output NEW`` screens an earlier report again with the
current task definitions, without calling a model.

Provider is Ollama by default (``--provider localai`` for LocalAI); the
corpus is indexed with ``--embedder``. ``--variants`` picks a subset of
rag, agent_search, agent_search_calc.
"""

import argparse
import html
import json
import sys
from pathlib import Path
from typing import List, Optional

from ai_platform.backend.service_layer.macro.agent_benchmark.agent_rag_evaluator import (
    VARIANTS,
    evaluate_agent_rag,
    rescreen,
)
from ai_platform.backend.ui_layer.cli.benchmark_report_rendering import html_table, md_table
from ai_platform.common.llm.localai_adapter import LocalAIAdapter
from ai_platform.common.llm.ollama_adapter import OllamaAdapter
from ai_platform.common.rag.embedder import create_embedder

PROVIDERS = {"ollama": (OllamaAdapter, "http://127.0.0.1:11434"),
             "localai": (LocalAIAdapter, "http://127.0.0.1:8081")}
SUMMARY = [("model", "Model"), ("variant", "Variant"), ("correct", "Right (of 11)"),
           ("correct_lookup", "Lookup"), ("correct_lookup_calc", "Lookup + calc"),
           ("correct_general", "General"), ("retrieval_hit", "Facts found"),
           ("mean_model_calls", "Model calls"), ("mean_seconds", "Seconds"),
           ("not_answered", "Not answered")]
ROWS = [("model", "Model"), ("variant", "Variant"), ("task_id", "Task"), ("kind", "Kind"),
        ("question", "Question"), ("expected", "Expected"), ("answer", "Answer"),
        ("screening", "Screening"), ("tools_used", "Tools used"),
        ("retrieval_hit", "Facts found"), ("elapsed_seconds", "Seconds"),
        ("stop_reason", "Stop")]
CAVEAT = ("11 tasks about a fictional firm (facts only in the corpus), per model and "
          "variant: a small, targeted comparison, not a general agent benchmark. 'Right' is "
          "the rule-based screening (candidate_correct); 'Facts found' means the documents "
          "holding the facts were retrieved (rag) or returned by the agent's searches.")


def write_reports(report, output: Path, title: str) -> List[Path]:
    """JSON, HTML and Markdown next to each other."""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    rows = [{**r, "answer": " ".join(str(r["answer"] or "").split())[:200]}
            for r in report["results"]]
    safe = html.escape(title)
    output.with_suffix(".html").write_text(
        f'<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8"><title>{safe}</title>'
        "<style>body{font-family:sans-serif;margin:2rem}table{border-collapse:collapse;"
        "margin:1.5rem 0}th,td{border:1px solid #999;padding:.3rem .6rem;text-align:left;"
        "vertical-align:top}caption{text-align:left;font-weight:bold}</style></head><body>"
        f"<h1>{safe}</h1><p>{html.escape(CAVEAT)}</p>"
        + html_table("Summary", SUMMARY, report["summary"])
        + html_table("Every run", ROWS, rows) + "</body></html>\n", encoding="utf-8")
    output.with_suffix(".md").write_text("\n".join(
        [f"# {title}", "", f"> {CAVEAT}", "", "## Summary", "",
         md_table(SUMMARY, report["summary"]), "", "## Every run", "", md_table(ROWS, rows),
         ""]), encoding="utf-8")
    return [output, output.with_suffix(".html"), output.with_suffix(".md")]


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(prog="agent_rag_benchmark",
                                     description=__doc__.splitlines()[1].strip())
    parser.add_argument("--provider", choices=sorted(PROVIDERS), default="ollama")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--models", nargs="+")
    parser.add_argument("--rescreen", metavar="REPORT",
                        help="screen an existing report again with the current task "
                             "definitions (no model calls); writes to --output")
    parser.add_argument("--variants", nargs="+", choices=VARIANTS, default=list(VARIANTS))
    parser.add_argument("--agent-mode", choices=["auto", "native", "json"], default="auto")
    parser.add_argument("--embedder", default="ollama:bge-m3")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--max-steps", type=int, default=5)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--title", default="Agent with RAG: when does the tool loop help?")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    if args.rescreen:
        report = rescreen(json.loads(Path(args.rescreen).read_text(encoding="utf-8")))
        for path in write_reports(report, Path(args.output), args.title):
            print(path.resolve())
        return 0
    if not args.models:
        parser.error("--models is required (or --rescreen REPORT)")
    adapter_cls, default_url = PROVIDERS[args.provider]

    def factory(model):
        llm = adapter_cls()
        llm.initialize({"model": model, "base_url": args.base_url or default_url,
                        "temperature": 0, "max_tokens": args.max_tokens,
                        "timeout": args.timeout})
        return llm

    report = evaluate_agent_rag(args.models, factory, create_embedder(args.embedder),
                                variants=args.variants, top_k=args.top_k,
                                agent_mode=args.agent_mode, max_steps=args.max_steps,
                                progress=lambda m: print(m, file=sys.stderr))
    for path in write_reports(report, Path(args.output), args.title):
        print(path.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
