"""D3 adapter: generates D3 v7 drawing code.

D3 runs in the browser, so this adapter generates the JavaScript that draws
the chart with D3 (scales, axes, line/bar/point/histogram marks); the data
is embedded as JSON. ``plot`` returns the script; ``save`` writes .js or an
.html page loading D3 from the CDN. The script is syntax-checked in the
unit tests (``node --check``) but has not been rendered in a browser here.

Previously a stub returning a dict; the class name and the
VisualizationAdapter methods are unchanged.
"""

import json

from ai_platform.common.visualization.base import VisualizationAdapter
from ai_platform.common.visualization.chart_data import Chart, ChartAdapterBase, histogram

HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script></head>
<body><div id="chart" role="img" aria-label="{title}"></div>
<script>
{script}
</script></body></html>
"""

SCRIPT = """(function () {{
  const spec = {spec};
  const margin = {{top: 30, right: 20, bottom: 40, left: 50}};
  const width = spec.width - margin.left - margin.right;
  const height = spec.height - margin.top - margin.bottom;
  const svg = d3.select("#chart").append("svg")
      .attr("width", spec.width).attr("height", spec.height);
  const g = svg.append("g").attr("transform", `translate(${{margin.left}},${{margin.top}})`);
  const color = d3.scaleOrdinal(d3.schemeCategory10);
  const all = spec.series.flatMap(s => s.values);
  const y = d3.scaleLinear().domain([Math.min(0, d3.min(all)), d3.max(all)]).nice().range([height, 0]);
  let x;
  if (spec.type === "bar" || spec.type === "hist") {{
    x = d3.scaleBand().domain(spec.labels).range([0, width]).padding(spec.type === "hist" ? 0 : 0.1);
    const inner = d3.scaleBand().domain(spec.series.map(s => s.name)).range([0, x.bandwidth()]);
    spec.series.forEach(s => g.selectAll(null).data(s.values).join("rect")
        .attr("x", (d, i) => x(spec.labels[i]) + inner(s.name)).attr("width", inner.bandwidth())
        .attr("y", d => y(Math.max(0, d))).attr("height", d => Math.abs(y(d) - y(0)))
        .attr("fill", color(s.name)));
  }} else {{
    x = d3.scaleLinear().domain(d3.extent(spec.x)).range([0, width]);
    spec.series.forEach(s => {{
      const points = s.values.map((v, i) => [spec.x[i], v]);
      if (spec.type === "line") {{
        g.append("path").datum(points).attr("fill", "none").attr("stroke", color(s.name))
            .attr("d", d3.line().x(d => x(d[0])).y(d => y(d[1])));
      }} else {{
        g.selectAll(null).data(points).join("circle").attr("r", 3)
            .attr("cx", d => x(d[0])).attr("cy", d => y(d[1])).attr("fill", color(s.name));
      }}
    }});
  }}
  g.append("g").attr("transform", `translate(0,${{height}})`).call(d3.axisBottom(x));
  g.append("g").call(d3.axisLeft(y));
  svg.append("text").attr("x", spec.width / 2).attr("y", 18).attr("text-anchor", "middle")
      .text(spec.title);
}})();
"""


def d3_spec(chart: Chart):
    """Data handed to the generated script."""
    if chart.plot_type == "hist":
        series, labels = [], []
        for name, values in chart.series.items():
            edges, counts = histogram(values, chart.bins)
            labels = [f"{edges[i]:.3g}" for i in range(len(counts))]
            series.append({"name": name, "values": counts})
        return {"type": "hist", "labels": labels, "x": [], "series": series,
                "title": chart.title, "width": chart.width, "height": chart.height}
    return {"type": chart.plot_type, "labels": [str(v) for v in chart.x], "x": chart.x,
            "series": [{"name": n, "values": v} for n, v in chart.series.items()],
            "title": chart.title, "width": chart.width, "height": chart.height}


class D3Adapter(ChartAdapterBase, VisualizationAdapter):
    """D3 drawing code."""

    LIBRARY = "D3"
    FORMATS = (".js", ".html")

    def draw(self, chart: Chart):
        return SCRIPT.format(spec=json.dumps(d3_spec(chart), ensure_ascii=False))

    def export(self, figure, output_path: str, extension: str) -> None:
        with open(output_path, "w", encoding="utf-8") as handle:
            if extension == "js":
                handle.write(figure)
            else:
                handle.write(HTML.format(title=self.chart.title or "chart", script=figure))
