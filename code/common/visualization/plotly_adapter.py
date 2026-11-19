"""Plotly adapter.

Builds a ``plotly.graph_objects.Figure`` (``Scatter`` lines/markers,
``Bar``, ``Histogram``). ``save`` writes:

- .html - interactive page; plotly.js from the CDN unless
  ``include_plotlyjs`` (config) is True (then embedded, ~3.5 MB);
- .json - the figure specification;
- .png / .svg / .pdf - static images, which need the ``kaleido`` package.

Previously a stub returning a dict; the class name and the
VisualizationAdapter methods are unchanged.
"""

from ai_platform.common.visualization.base import VisualizationAdapter
from ai_platform.common.visualization.chart_data import (
    Chart,
    ChartAdapterBase,
    VisualizationError,
)


class PlotlyAdapter(ChartAdapterBase, VisualizationAdapter):
    """Interactive charts with Plotly."""

    LIBRARY = "Plotly"
    FORMATS = (".html", ".json", ".png", ".svg", ".pdf")

    def _setup(self) -> None:
        try:
            import plotly.graph_objects as go  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise VisualizationError("PlotlyAdapter requires: pip install plotly") from exc
        self._go = go  # pylint: disable=attribute-defined-outside-init

    def draw(self, chart: Chart):
        go = self._go
        figure = go.Figure()
        for name, values in chart.series.items():
            if chart.plot_type == "line":
                figure.add_trace(go.Scatter(x=chart.x, y=values, mode="lines", name=name))
            elif chart.plot_type == "scatter":
                figure.add_trace(go.Scatter(x=chart.x, y=values, mode="markers", name=name))
            elif chart.plot_type == "bar":
                figure.add_trace(go.Bar(x=chart.x, y=values, name=name))
            else:
                figure.add_trace(go.Histogram(x=values, nbinsx=chart.bins, name=name))
        figure.update_layout(title=chart.title, xaxis_title=chart.xlabel,
                             yaxis_title=chart.ylabel, width=chart.width, height=chart.height,
                             barmode="group" if chart.plot_type == "bar" else "overlay")
        return figure

    def export(self, figure, output_path: str, extension: str) -> None:
        if extension == "html":
            figure.write_html(output_path, include_plotlyjs=True
                              if self.defaults.get("include_plotlyjs") else "cdn")
        elif extension == "json":
            figure.write_json(output_path)
        else:
            try:
                figure.write_image(output_path)
            except (ValueError, ImportError) as exc:
                raise VisualizationError(
                    f"static export needs kaleido (pip install kaleido): {exc}") from exc
