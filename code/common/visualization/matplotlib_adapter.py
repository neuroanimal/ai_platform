"""Matplotlib adapter.

Draws with the object-oriented Matplotlib API on a non-interactive (Agg)
figure, so it works headless and never touches pyplot's global state.
``plot`` returns the ``matplotlib.figure.Figure``; ``save`` writes .png,
.svg, .pdf, .jpg or .eps (``dpi`` config/kwarg, default 100).

Previously a stub returning a dict; the class name and the
VisualizationAdapter methods are unchanged.
"""

from ai_platform.common.visualization.base import VisualizationAdapter
from ai_platform.common.visualization.chart_data import (
    Chart,
    ChartAdapterBase,
    VisualizationError,
    histogram,
)


def draw_on_axes(axes, chart: Chart) -> None:
    """Draw ``chart`` on Matplotlib axes (shared with the seaborn adapter's fallback)."""
    if chart.plot_type == "hist":
        for name, values in chart.series.items():
            edges, _ = histogram(values, chart.bins)
            axes.hist(values, bins=edges, alpha=0.7, label=name)
    else:
        count = len(chart.series)
        for index, (name, values) in enumerate(chart.series.items()):
            if chart.plot_type == "line":
                axes.plot(chart.x, values, label=name)
            elif chart.plot_type == "scatter":
                axes.scatter(chart.x, values, label=name)
            else:  # grouped bars
                width = 0.8 / count
                positions = [i + (index - (count - 1) / 2) * width for i in range(len(chart.x))]
                axes.bar(positions, values, width=width, label=name)
        if chart.plot_type == "bar":
            axes.set_xticks(range(len(chart.x)))
            axes.set_xticklabels([str(x) for x in chart.x])
    axes.set_title(chart.title)
    axes.set_xlabel(chart.xlabel)
    axes.set_ylabel(chart.ylabel)
    if len(chart.series) > 1:
        axes.legend()


class MatplotlibAdapter(ChartAdapterBase, VisualizationAdapter):
    """Charts with Matplotlib (Agg)."""

    LIBRARY = "Matplotlib"
    FORMATS = (".png", ".svg", ".pdf", ".jpg", ".eps")

    def _setup(self) -> None:
        try:
            from matplotlib.figure import Figure  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise VisualizationError("MatplotlibAdapter requires: pip install matplotlib") from exc
        self._figure_cls = Figure  # pylint: disable=attribute-defined-outside-init

    def draw(self, chart: Chart):
        figure = self._figure_cls(figsize=(chart.width / 100, chart.height / 100))
        draw_on_axes(figure.add_subplot(), chart)
        figure.tight_layout()
        return figure

    def export(self, figure, output_path: str, extension: str) -> None:
        figure.savefig(output_path, dpi=self.defaults.get("dpi", 100))
