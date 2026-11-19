"""ggplot2 adapter (R, run through ``Rscript``).

``plot`` returns an R script that builds the chart with ggplot2 from the
chart's long-format records (embedded as an R data frame); ``save`` runs
that script with ``Rscript`` for real, ending in ``ggsave(<output>)``
(.png, .pdf, .svg - .svg needs the R package ``svglite``).

Needs R with the ggplot2 package; not verified here (R is not installed in
the development environment), unit tests check the generated script and
command. For ggplot-style charts in Python, plotnine is the closest
equivalent. Configuration: ``timeout`` (default 120), ``executable``,
``runner`` (tests), ``dpi`` (default 100).

Previously a stub returning a dict; the class name and the
VisualizationAdapter methods are unchanged.
"""

import os
import tempfile

from ai_platform.common.util.cli_runner import CLIToolMixin
from ai_platform.common.visualization.base import VisualizationAdapter
from ai_platform.common.visualization.chart_data import (
    Chart,
    ChartAdapterBase,
    VisualizationError,
)


def r_string(text) -> str:
    """R string literal."""
    return '"' + str(text).replace("\\", "\\\\").replace('"', '\\"') + '"'


def r_vector(values) -> str:
    """R vector literal of numbers or strings."""
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
        return "c(" + ", ".join(repr(float(v)) for v in values) + ")"
    return "c(" + ", ".join(r_string(v) for v in values) + ")"


def ggplot_script(chart: Chart) -> str:
    """R code creating ``p``, a ggplot object for ``chart``."""
    rows = chart.records()
    data = (f"df <- data.frame(x = {r_vector([r['x'] for r in rows])}, "
            f"y = {r_vector([r['y'] for r in rows])}, "
            f"series = {r_vector([r['series'] for r in rows])})")
    if chart.plot_type == "hist":
        layer = f"ggplot(df, aes(x = y, fill = series)) + geom_histogram(bins = {chart.bins})"
    else:
        geom = {"line": "geom_line()", "scatter": "geom_point()",
                "bar": 'geom_col(position = "dodge")'}[chart.plot_type]
        aes = "aes(x = factor(x), y = y, fill = series)" if chart.plot_type == "bar" \
            else "aes(x = x, y = y, colour = series)"
        layer = f"ggplot(df, {aes}) + {geom}"
    labels = (f"labs(title = {r_string(chart.title)}, x = {r_string(chart.xlabel)}, "
              f"y = {r_string(chart.ylabel)})")
    return "\n".join(["suppressPackageStartupMessages(library(ggplot2))", data,
                      f"p <- {layer} + {labels}", ""])


class GGPlot2Adapter(CLIToolMixin, ChartAdapterBase, VisualizationAdapter):
    """ggplot2 charts rendered by Rscript."""

    LIBRARY = "ggplot2"
    FORMATS = (".png", ".pdf", ".svg")
    TOOLS = ["Rscript"]
    HINT = "install R and the ggplot2 package"
    ERROR = VisualizationError

    def _setup(self) -> None:
        self._configure_cli(self.defaults)

    def draw(self, chart: Chart):
        return ggplot_script(chart)

    def export(self, figure, output_path: str, extension: str) -> None:
        chart = self.chart
        script = figure + (
            f"ggsave({r_string(os.path.abspath(output_path))}, p, "
            f"width = {chart.width / 100}, height = {chart.height / 100}, "
            f"dpi = {int(self.defaults.get('dpi', 100))})\n")
        with tempfile.TemporaryDirectory(prefix="ai_platform_r_") as work:
            path = os.path.join(work, "chart.R")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(script)
            self._run_cli([self.executable, path], cwd=work)
