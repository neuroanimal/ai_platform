"""Vega-Lite adapter: chart specifications in the Vega-Lite v5 JSON grammar.

Vega-Lite is a declarative JSON grammar, so the specification is generated
in Python (stdlib only) and is the real artefact; rendering happens in any
Vega-Lite runtime. ``plot`` returns the spec as a dict; ``save`` writes:

- .json / .vl.json - the specification;
- .html - a page rendering it with vega-embed from the CDN.

Previously a stub returning a dict; the class name and the
VisualizationAdapter methods are unchanged.
"""

import json
from typing import Any, Dict

from ai_platform.common.visualization.base import VisualizationAdapter
from ai_platform.common.visualization.chart_data import Chart, ChartAdapterBase

SCHEMA = "https://vega.github.io/schema/vega-lite/v5.json"
HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script></head>
<body><div id="chart" role="img" aria-label="{title}"></div>
<script>vegaEmbed("#chart", {spec});</script></body></html>
"""


def vega_lite_spec(chart: Chart) -> Dict[str, Any]:
    """Vega-Lite v5 specification for ``chart``."""
    numeric_x = all(isinstance(v, (int, float)) for v in chart.x)
    spec: Dict[str, Any] = {
        "$schema": SCHEMA,
        "title": chart.title,
        "width": chart.width,
        "height": chart.height,
        "data": {"values": chart.records()},
    }
    color = {"color": {"field": "series", "type": "nominal"}} if len(chart.series) > 1 else {}
    if chart.plot_type == "hist":
        spec["mark"] = "bar"
        spec["encoding"] = {
            "x": {"field": "y", "type": "quantitative", "bin": {"maxbins": chart.bins},
                  "title": chart.xlabel or "value"},
            "y": {"aggregate": "count", "type": "quantitative", "title": chart.ylabel or "count"},
            **color}
        return spec
    spec["mark"] = {"line": "line", "bar": "bar", "scatter": "point"}[chart.plot_type]
    x_type = "quantitative" if numeric_x and chart.plot_type != "bar" else "ordinal"
    spec["encoding"] = {
        "x": {"field": "x", "type": x_type, "title": chart.xlabel},
        "y": {"field": "y", "type": "quantitative", "title": chart.ylabel},
        **color,
        **({"xOffset": {"field": "series"}} if color and chart.plot_type == "bar" else {}),
    }
    return spec


class VegaLiteAdapter(ChartAdapterBase, VisualizationAdapter):
    """Vega-Lite specifications."""

    LIBRARY = "Vega-Lite"
    FORMATS = (".json", ".html")

    def draw(self, chart: Chart):
        return vega_lite_spec(chart)

    def export(self, figure, output_path: str, extension: str) -> None:
        with open(output_path, "w", encoding="utf-8") as handle:
            if extension == "json":
                json.dump(figure, handle, ensure_ascii=False, indent=2)
            else:
                handle.write(HTML.format(title=figure.get("title", "chart"),
                                         spec=json.dumps(figure, ensure_ascii=False)))
