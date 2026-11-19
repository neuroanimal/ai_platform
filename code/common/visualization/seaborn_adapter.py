"""Seaborn adapter.

Draws with seaborn's axes-level functions (``lineplot``, ``barplot``,
``scatterplot``, ``histplot``) on a non-interactive Matplotlib figure, from
the long-format records of the chart (pandas DataFrame). ``plot`` returns
the Matplotlib ``Figure``; ``save`` writes .png, .svg, .pdf or .jpg.

Previously a stub returning a dict; the class name and the
VisualizationAdapter methods are unchanged.
"""

from ai_platform.common.visualization.base import VisualizationAdapter
from ai_platform.common.visualization.chart_data import (
    Chart,
    ChartAdapterBase,
    VisualizationError,
)


class SeabornAdapter(ChartAdapterBase, VisualizationAdapter):
    """Charts with seaborn."""

    LIBRARY = "Seaborn"
    FORMATS = (".png", ".svg", ".pdf", ".jpg")

    def _setup(self) -> None:
        try:
            import pandas  # pylint: disable=import-outside-toplevel
            import seaborn  # pylint: disable=import-outside-toplevel
            from matplotlib.figure import Figure  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise VisualizationError("SeabornAdapter requires: pip install seaborn") from exc
        # pylint: disable=attribute-defined-outside-init
        self._sns, self._pd, self._figure_cls = seaborn, pandas, Figure

    def draw(self, chart: Chart):
        figure = self._figure_cls(figsize=(chart.width / 100, chart.height / 100))
        axes = figure.add_subplot()
        frame = self._pd.DataFrame(chart.records())
        hue = "series" if len(chart.series) > 1 else None
        if chart.plot_type == "line":
            self._sns.lineplot(data=frame, x="x", y="y", hue=hue, ax=axes)
        elif chart.plot_type == "scatter":
            self._sns.scatterplot(data=frame, x="x", y="y", hue=hue, ax=axes)
        elif chart.plot_type == "bar":
            self._sns.barplot(data=frame, x="x", y="y", hue=hue, ax=axes)
        else:
            self._sns.histplot(data=frame, x="y", hue=hue, bins=chart.bins, ax=axes)
        axes.set_title(chart.title)
        axes.set_xlabel(chart.xlabel or ("value" if chart.plot_type == "hist" else ""))
        axes.set_ylabel(chart.ylabel)
        figure.tight_layout()
        return figure

    def export(self, figure, output_path: str, extension: str) -> None:
        figure.savefig(output_path, dpi=self.defaults.get("dpi", 100))
