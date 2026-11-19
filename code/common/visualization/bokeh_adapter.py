"""Bokeh adapter.

Builds a ``bokeh.plotting.figure`` (``line``, ``vbar`` with dodged groups,
``scatter``, histogram as ``quad``). ``save`` writes a standalone .html
page (BokehJS from the CDN) with ``bokeh.io.save``; .png needs Bokeh's
selenium-based export and is not offered.

Not verified against an installed Bokeh here (the package was not
installed when this was written). Previously a stub returning a dict; the
class name and the VisualizationAdapter methods are unchanged.
"""

from ai_platform.common.visualization.base import VisualizationAdapter
from ai_platform.common.visualization.chart_data import (
    Chart,
    ChartAdapterBase,
    VisualizationError,
    histogram,
)

PALETTE = ("#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b")


class BokehAdapter(ChartAdapterBase, VisualizationAdapter):
    """Charts with Bokeh."""

    LIBRARY = "Bokeh"
    FORMATS = (".html",)

    def _setup(self) -> None:
        try:
            from bokeh import io, plotting, resources  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise VisualizationError("BokehAdapter requires: pip install bokeh") from exc
        # pylint: disable=attribute-defined-outside-init
        self._io, self._plotting, self._resources = io, plotting, resources

    def draw(self, chart: Chart):
        categorical = chart.plot_type == "bar"
        x_range = [str(v) for v in chart.x] if categorical else None
        fig = self._plotting.figure(title=chart.title, width=chart.width, height=chart.height,
                                    x_axis_label=chart.xlabel, y_axis_label=chart.ylabel,
                                    **({"x_range": x_range} if x_range else {}))
        count = len(chart.series)
        for index, (name, values) in enumerate(chart.series.items()):
            color = PALETTE[index % len(PALETTE)]
            if chart.plot_type == "line":
                fig.line(chart.x, values, legend_label=name, color=color)
            elif chart.plot_type == "scatter":
                fig.scatter(chart.x, values, legend_label=name, color=color)
            elif chart.plot_type == "bar":
                width = 0.8 / count
                offset = (index - (count - 1) / 2) * width
                fig.vbar(x=[(i + 0.5 + offset) for i in range(len(values))], top=values,
                         width=width, legend_label=name, color=color)
            else:
                edges, counts = histogram(values, chart.bins)
                fig.quad(top=counts, bottom=0, left=edges[:-1], right=edges[1:],
                         alpha=0.6, legend_label=name, color=color)
        return fig

    def export(self, figure, output_path: str, extension: str) -> None:
        self._io.save(figure, filename=output_path, resources=self._resources.CDN,
                      title=self.chart.title or "chart")
