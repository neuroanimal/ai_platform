"""
Render a benchmark summary (``service_layer.macro.llm_benchmark.benchmark_summary``)
as an HTML page with real ``<table>`` markup, or as Markdown.

HTML: every value is escaped (``html.escape``), tables have a ``<caption>``
and ``<th scope=...>`` headers for screen readers, and the page has a
``lang`` attribute and no scripts. The caveat that screening is not a
verdict is part of the page, not a footnote somewhere else.
"""

import html
from typing import Any, Dict, Iterable, List, Sequence

CAVEAT = ("Screening is a rule-based pre-assessment, not a verdict: 'correct' and "
          "'incorrect' are candidates, 'manual review' needs a human. Latency is wall-clock "
          "time per request after a warm-up, on this machine.")

MODEL_COLUMNS = [("model", "Model"), ("language", "Lang"), ("answered", "Answered"),
                 ("requests", "Requests"), ("median_seconds", "Median s"),
                 ("p90_seconds", "p90 s"), ("truncated", "Truncated"),
                 ("correct", "Correct"), ("incorrect", "Incorrect"), ("partial", "Partial"),
                 ("manual_review", "Manual review")]
TASK_COLUMNS = [("task", "Task"), ("language", "Lang"), ("model", "Model"),
                ("majority", "Majority outcome"), ("consistent", "Runs agree"),
                ("runs", "All runs")]
WARMUP_COLUMNS = [("model", "Model"), ("status", "Status"),
                  ("load_and_warmup_seconds", "Load + first answer s"), ("error", "Error")]


def _cell(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return "" if value is None else str(value)


def _header(summary: Dict[str, Any]) -> List[str]:
    return [f"Task set: {summary['task_set']}",
            f"Provider: {summary['provider']} ({summary['endpoint']})",
            f"Repeats: {summary['repeats']}, temperature {summary['temperature']}, "
            f"max_tokens {summary['max_tokens']}",
            f"Run started (UTC): {summary['created_at_utc']}",
            f"Screening version: {summary['screening_version']}",
            f"Task/model cells whose runs disagree: {summary['inconsistent_runs']}"]


def _html_table(caption: str, columns: Sequence, rows: Iterable[Dict[str, Any]]) -> str:
    esc = html.escape
    head = "".join(f'<th scope="col">{esc(title)}</th>' for _, title in columns)
    body = []
    for row in rows:
        cells = [f'<th scope="row">{esc(_cell(row[columns[0][0]]))}</th>']
        cells += [f"<td>{esc(_cell(row.get(key)))}</td>" for key, _ in columns[1:]]
        body.append("<tr>" + "".join(cells) + "</tr>")
    return (f"<table>\n<caption>{esc(caption)}</caption>\n<thead><tr>{head}</tr></thead>\n"
            f"<tbody>\n" + "\n".join(body) + "\n</tbody>\n</table>")


def render_html(summary: Dict[str, Any], title: str = "LLM benchmark") -> str:
    """Standalone HTML page."""
    esc = html.escape
    header = "".join(f"<li>{esc(line)}</li>" for line in _header(summary))
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>{esc(title)}</title>
<style>
body {{ font-family: sans-serif; margin: 2rem; color: #111; }}
table {{ border-collapse: collapse; margin: 1.5rem 0; }}
caption {{ text-align: left; font-weight: bold; padding: .4rem 0; }}
th, td {{ border: 1px solid #999; padding: .3rem .6rem; text-align: left; }}
thead th {{ background: #e8e8e8; }}
.caveat {{ border-left: 4px solid #b36b00; padding: .5rem 1rem; background: #fff6e5; }}
</style></head>
<body>
<h1>{esc(title)}</h1>
<p class="caveat">{esc(CAVEAT)}</p>
<ul>{header}</ul>
{_html_table("Models by screening outcome", MODEL_COLUMNS, summary["models"])}
{_html_table("Warm-up (model load + first answer)", WARMUP_COLUMNS, summary["warmup"])}
{_html_table("Outcome per task, language and model", TASK_COLUMNS, summary["tasks"])}
</body></html>
"""


def _md_table(columns: Sequence, rows: Iterable[Dict[str, Any]]) -> str:
    lines = ["| " + " | ".join(title for _, title in columns) + " |",
             "|" + "---|" * len(columns)]
    for row in rows:
        lines.append("| " + " | ".join(_cell(row.get(key)).replace("|", "\\|")
                                       for key, _ in columns) + " |")
    return "\n".join(lines)


def render_markdown(summary: Dict[str, Any], title: str = "LLM benchmark") -> str:
    """Markdown version of the same tables."""
    parts = [f"# {title}", "", f"> {CAVEAT}", ""]
    parts += [f"- {line}" for line in _header(summary)]
    parts += ["", "## Models by screening outcome", "", _md_table(MODEL_COLUMNS, summary["models"]),
              "", "## Warm-up", "", _md_table(WARMUP_COLUMNS, summary["warmup"]),
              "", "## Outcome per task, language and model", "",
              _md_table(TASK_COLUMNS, summary["tasks"]), ""]
    return "\n".join(parts)
