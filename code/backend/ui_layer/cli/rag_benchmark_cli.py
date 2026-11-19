"""
Command line for comparing embedders on a retrieval set.

    python -m ai_platform.backend.ui_layer.cli.rag_benchmark_cli list
    python -m ai_platform.backend.ui_layer.cli.rag_benchmark_cli run \\
        --embedders hashing ollama:bge-m3 ollama:nomic-embed-text \\
        --output results/retrieval_bilingual.json
    python -m ai_platform.backend.ui_layer.cli.rag_benchmark_cli qa \\
        --provider ollama --models bielik-4.5b-v3:q8_0 gemma3:4b \\
        --embedder ollama:bge-m3 --output results/rag_qa.json

``qa`` answers the QA set closed-book and with retrieved context, per model.

Embedder names:

    hashing[:<dimension>]      lexical HashingEmbedder (no model, no server)
    ollama:<model>             Ollama /v1/embeddings (--ollama-url)
    localai:<model>            LocalAI /v1/embeddings (--localai-url)
    st:<model>                 local sentence-transformers model

Writes the JSON report plus ``.html`` and ``.md`` tables next to it.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from ai_platform.backend.service_layer.macro.rag_benchmark.qa_evaluator import (
    evaluate_qa,
    get_qa_set,
)
from ai_platform.backend.service_layer.macro.rag_benchmark.retrieval_evaluator import (
    evaluate_embedders,
    get_retrieval_set,
    list_retrieval_sets,
)
from ai_platform.backend.ui_layer.cli.benchmark_report_rendering import html_table, md_table
from ai_platform.common.llm.localai_adapter import LocalAIAdapter
from ai_platform.common.llm.ollama_adapter import OllamaAdapter
from ai_platform.common.llm.openai_compatible_adapter import OpenAICompatibleAdapter
from ai_platform.common.rag.embedder import create_embedder

PROVIDERS = {"ollama": (OllamaAdapter, "http://127.0.0.1:11434"),
             "localai": (LocalAIAdapter, "http://127.0.0.1:8081"),
             "openai-compatible": (OpenAICompatibleAdapter, None)}
QA_SUMMARY_COLUMNS = [("model", "Model"), ("mode", "Mode"), ("questions", "Questions"),
                      ("n", "N"), ("correct", "Correct"), ("incorrect", "Incorrect"),
                      ("manual_review", "Manual review"), ("median_seconds", "Median s")]
QA_ROW_COLUMNS = [("model", "Model"), ("mode", "Mode"), ("item_id", "Item"),
                  ("question", "Question"), ("expected", "Expected"), ("retrieved", "Retrieved"),
                  ("screening", "Screening"), ("answer", "Answer")]

SUMMARY_COLUMNS = [("embedder", "Embedder"), ("status", "Status"), ("hit@1", "Hit@1"),
                   ("hit@3", "Hit@3"), ("mrr", "MRR"), ("recall@5", "Recall@5"),
                   ("index_seconds", "Index s"), ("query_seconds_mean", "s / query"),
                   ("error", "Error")]
DIRECTION_COLUMNS = [("embedder", "Embedder"), ("direction", "Direction"), ("hit@1", "Hit@1"),
                     ("hit@3", "Hit@3"), ("mrr", "MRR")]
QUERY_COLUMNS = [("embedder", "Embedder"), ("query_id", "Query"), ("direction", "Direction"),
                 ("query", "Text"), ("relevant", "Relevant"), ("ranked", "Retrieved (best first)"),
                 ("rr", "RR")]
CAVEAT = ("16 queries on 12 documents: a quick, reproducible comparison, not a benchmark "
          "of general retrieval quality. Most queries are cross-lingual on purpose.")


def make_factory(args):
    """name -> Embedder (naming scheme: ``common.rag.embedder.create_embedder``)."""
    def factory(name: str):
        return create_embedder(name, ollama_url=args.ollama_url, localai_url=args.localai_url)
    return factory


def rows(report):
    """(summary, by-direction, per-query) table rows."""
    summary, directions, queries = [], [], []
    for result in report["results"]:
        metrics = {k: round(v, 3) for k, v in result.get("metrics", {}).items()}
        summary.append({**result, **metrics})
        for direction, values in result.get("by_direction", {}).items():
            directions.append({"embedder": result["embedder"], "direction": direction,
                               **{k: round(v, 3) for k, v in values.items()}})
        queries.extend({**q, "rr": round(q["rr"], 3)} for q in result.get("queries", []))
    return summary, directions, queries


def render(report, title: str):
    """(html, markdown) for a report."""
    summary, directions, queries = rows(report)
    head = (f"Retrieval set {report['retrieval_set']}@{report['retrieval_set_version']}: "
            f"{report['documents']} documents, {report['queries']} queries, "
            f"top_k {report['top_k']}, run {report['created_at_utc']}")
    page = (f'<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8"><title>{title}</title>'
            "<style>body{font-family:sans-serif;margin:2rem}table{border-collapse:collapse;"
            "margin:1.5rem 0}th,td{border:1px solid #999;padding:.3rem .6rem;text-align:left}"
            "caption{text-align:left;font-weight:bold}</style></head><body>"
            f"<h1>{title}</h1><p>{CAVEAT}</p><p>{head}</p>"
            + html_table("Embedders", SUMMARY_COLUMNS, summary)
            + html_table("By query direction", DIRECTION_COLUMNS, directions)
            + html_table("Every query", QUERY_COLUMNS, queries) + "</body></html>\n")
    markdown = "\n".join([f"# {title}", "", f"> {CAVEAT}", "", head, "", "## Embedders", "",
                          md_table(SUMMARY_COLUMNS, summary), "", "## By query direction", "",
                          md_table(DIRECTION_COLUMNS, directions), "", "## Every query", "",
                          md_table(QUERY_COLUMNS, queries), ""])
    return page, markdown


def command_run(args) -> int:
    """Evaluate embedders and write JSON, HTML and Markdown."""
    report = evaluate_embedders(get_retrieval_set(args.retrieval_set), args.embedders,
                                make_factory(args), top_k=args.top_k)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    import html as html_module  # pylint: disable=import-outside-toplevel
    page, markdown = render(report, html_module.escape(args.title or "Retrieval benchmark"))
    output.with_suffix(".html").write_text(page, encoding="utf-8")
    output.with_suffix(".md").write_text(markdown, encoding="utf-8")
    for path in (output, output.with_suffix(".html"), output.with_suffix(".md")):
        print(path.resolve())
    return 0 if any(r["status"] == "PASS" for r in report["results"]) else 1


def command_qa(args) -> int:
    """Closed-book vs RAG question answering; JSON + HTML + Markdown."""
    adapter_cls, default_url = PROVIDERS[args.provider]

    def llm_factory(model):
        llm = adapter_cls()
        llm.initialize({"model": model, "base_url": args.base_url or default_url,
                        "temperature": 0, "max_tokens": args.max_tokens,
                        "timeout": args.timeout})
        return llm

    report = evaluate_qa(get_qa_set(args.qa_set), args.models, llm_factory,
                         create_embedder(args.embedder, ollama_url=args.ollama_url,
                                         localai_url=args.localai_url),
                         embedder_name=args.embedder, top_k=args.top_k,
                         progress=lambda m: print(m, file=sys.stderr))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    import html as html_module  # pylint: disable=import-outside-toplevel
    title = html_module.escape(args.title or "RAG question answering: closed-book vs RAG")
    caveat = ("Screening is a rule-based pre-assessment, not a verdict. 'fictional' questions "
              "are about invented facts that only the corpus contains.")
    head = (f"QA set {report['qa_set']}@{report['qa_set_version']}, embedder "
            f"{report['embedder']}, top_k {report['top_k']}, retrieval hit rate "
            f"{report['retrieval_hit_rate']:.2f}, run {report['created_at_utc']}")
    rows_ = [{**r, "answer": " ".join(str(r.get("answer", r.get("error", ""))).split())[:300]}
             for r in report["results"]]
    output.with_suffix(".html").write_text(
        f'<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8"><title>{title}</title>'
        "<style>body{font-family:sans-serif;margin:2rem}table{border-collapse:collapse;"
        "margin:1.5rem 0}th,td{border:1px solid #999;padding:.3rem .6rem;text-align:left;"
        "vertical-align:top}caption{text-align:left;font-weight:bold}</style></head><body>"
        f"<h1>{title}</h1><p>{caveat}</p><p>{html_module.escape(head)}</p>"
        + html_table("Summary", QA_SUMMARY_COLUMNS, report["summary"])
        + html_table("Every answer", QA_ROW_COLUMNS, rows_) + "</body></html>\n",
        encoding="utf-8")
    output.with_suffix(".md").write_text("\n".join([
        f"# {title}", "", f"> {caveat}", "", head, "", "## Summary", "",
        md_table(QA_SUMMARY_COLUMNS, report["summary"]), "", "## Every answer", "",
        md_table(QA_ROW_COLUMNS, rows_), ""]), encoding="utf-8")
    for path in (output, output.with_suffix(".html"), output.with_suffix(".md")):
        print(path.resolve())
    return 0 if any(r["status"] == "PASS" for r in report["results"]) else 1


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(prog="rag_benchmark", description=__doc__.splitlines()[1])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list").set_defaults(func=lambda a: print("\n".join(list_retrieval_sets())) or 0)
    run = sub.add_parser("run")
    run.add_argument("--retrieval-set", default="bilingual_retrieval")
    run.add_argument("--embedders", nargs="+", default=["hashing", "ollama:bge-m3"])
    run.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    run.add_argument("--localai-url", default="http://127.0.0.1:8081")
    run.add_argument("--top-k", type=int, default=5)
    run.add_argument("--title", default=None)
    run.add_argument("--output", required=True)
    run.set_defaults(func=command_run)
    qa = sub.add_parser("qa", help="closed-book vs RAG question answering")
    qa.add_argument("--qa-set", default="bilingual_qa")
    qa.add_argument("--provider", choices=sorted(PROVIDERS), default="ollama")
    qa.add_argument("--base-url", default=None)
    qa.add_argument("--models", nargs="+", required=True)
    qa.add_argument("--embedder", default="ollama:bge-m3")
    qa.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    qa.add_argument("--localai-url", default="http://127.0.0.1:8081")
    qa.add_argument("--top-k", type=int, default=3)
    qa.add_argument("--max-tokens", type=int, default=256)
    qa.add_argument("--timeout", type=float, default=600.0)
    qa.add_argument("--title", default=None)
    qa.add_argument("--output", required=True)
    qa.set_defaults(func=command_qa)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
