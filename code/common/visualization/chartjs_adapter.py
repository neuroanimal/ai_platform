"""Chart.js adapter: Chart.js v4 configuration objects.

Chart.js is configured with a JSON-compatible object, so the configuration
is generated in Python (stdlib only); rendering happens in the browser.
``plot`` returns the config dict; ``save`` writes .json (the config) or
.html (a page with a <canvas> rendering it with Chart.js from the CDN).
Histograms are pre-binned in Python (Chart.js has no histogram type).

Previously a stub returning a dict; the class name and the
VisualizationAdapter methods are unchanged.
"""

import json

from ai_platform.common.visualization.base import VisualizationAdapter
from ai_platform.common.visualization.chart_data import Chart, ChartAdapterBase, histogram

HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script></head>
<body><div style="width:{width}px;height:{height}px">
<canvas id="chart" role="img" aria-label="{title}"></canvas></div>
<script>new Chart(document.getElementById("chart"), {config});</script></body></html>
"""


def chartjs_config(chart: Chart):
    """Chart.js configuration for ``chart``."""
    titles = {"title": {"display": bool(chart.title), "text": chart.title}}
    scales = {"x": {"title": {"display": bool(chart.xlabel), "text": chart.xlabel}},
              "y": {"title": {"display": bool(chart.ylabel), "text": chart.ylabel}}}
    if chart.plot_type == "hist":
        datasets, labels = [], []
        for name, values in chart.series.items():
            edges, counts = histogram(values, chart.bins)
            labels = [f"{edges[i]:.3g}-{edges[i + 1]:.3g}" for i in range(len(counts))]
            datasets.append({"label": name, "data": counts})
        return {"type": "bar", "data": {"labels": labels, "datasets": datasets},
                "options": {"plugins": titles, "scales": scales,
                            "datasets": {"bar": {"barPercentage": 1.0, "categoryPercentage": 1.0}}}}
    if chart.plot_type == "scatter":
        datasets = [{"label": name, "data": [{"x": x, "y": y} for x, y in zip(chart.x, values)]}
                    for name, values in chart.series.items()]
        return {"type": "scatter", "data": {"datasets": datasets},
                "options": {"plugins": titles, "scales": scales}}
    datasets = [{"label": name, "data": values} for name, values in chart.series.items()]
    return {"type": chart.plot_type, "data": {"labels": chart.x, "datasets": datasets},
            "options": {"plugins": titles, "scales": scales}}


class ChartJSAdapter(ChartAdapterBase, VisualizationAdapter):
    """Chart.js configurations."""

    LIBRARY = "Chart.js"
    FORMATS = (".json", ".html")

    def draw(self, chart: Chart):
        return chartjs_config(chart)

    def export(self, figure, output_path: str, extension: str) -> None:
        with open(output_path, "w", encoding="utf-8") as handle:
            if extension == "json":
                json.dump(figure, handle, ensure_ascii=False, indent=2)
            else:
                plugins = figure.get("options", {}).get("plugins", {})
                handle.write(HTML.format(title=plugins.get("title", {}).get("text") or "chart",
                                         width=self.chart.width, height=self.chart.height,
                                         config=json.dumps(figure, ensure_ascii=False)))
