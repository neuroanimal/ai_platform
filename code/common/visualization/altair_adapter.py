"""Altair adapter (Vega-Lite through the ``altair`` package).

Builds an ``altair.Chart`` from the chart's long-format records with the
same encodings as ``VegaLiteAdapter``. ``save`` writes .html or .json via
``Chart.save``; .png/.svg need Altair's ``vl-convert-python`` extra.

Not verified against an installed Altair here (the package was not
installed when this was written); ``VegaLiteAdapter`` produces the
equivalent specification without the dependency. Previously a stub
returning a dict; the class name and the VisualizationAdapter methods are
unchanged.
"""

from ai_platform.common.visualization.base import VisualizationAdapter
from ai_platform.common.visualization.chart_data import (
    Chart,
    ChartAdapterBase,
    VisualizationError,
)
from ai_platform.common.visualization.vegalite_adapter import vega_lite_spec


class AltairAdapter(ChartAdapterBase, VisualizationAdapter):
    """Charts with Altair."""

    LIBRARY = "Altair"
    FORMATS = (".html", ".json", ".png", ".svg")

    def _setup(self) -> None:
        try:
            import altair  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise VisualizationError("AltairAdapter requires: pip install altair") from exc
        self._alt = altair  # pylint: disable=attribute-defined-outside-init

    def draw(self, chart: Chart):
        # Altair accepts a full Vega-Lite dict and validates it against its schema.
        return self._alt.Chart.from_dict(vega_lite_spec(chart))

    def export(self, figure, output_path: str, extension: str) -> None:
        try:
            figure.save(output_path)
        except (ValueError, ImportError) as exc:
            raise VisualizationError(f"altair could not write {extension}: {exc}") from exc
