"""Example usage of visualization library adapters.

Registers every adapter and exercises each one with a small, real operation -
charts are written to a temporary directory. Nothing is fabricated: an adapter
whose tool, server or package is not available here is reported as skipped
with the reason.

    python -m ai_platform.common.example.visualization_example
"""

# Examples follow the same register-and-try pattern on purpose.
# pylint: disable=duplicate-code

import os
import tempfile

from ai_platform.common.visualization.altair_adapter import AltairAdapter
from ai_platform.common.visualization.bokeh_adapter import BokehAdapter
from ai_platform.common.visualization.chart_data import VisualizationError
from ai_platform.common.visualization.chartjs_adapter import ChartJSAdapter
from ai_platform.common.visualization.d3_adapter import D3Adapter
from ai_platform.common.visualization.ggplot2_adapter import GGPlot2Adapter
from ai_platform.common.visualization.matplotlib_adapter import MatplotlibAdapter
from ai_platform.common.visualization.plotly_adapter import PlotlyAdapter
from ai_platform.common.visualization.seaborn_adapter import SeabornAdapter
from ai_platform.common.visualization.vegalite_adapter import VegaLiteAdapter
from ai_platform.common.visualization.visualization_registry import get_registry


def main():
    """Register all adapters and exercise the usable ones."""
    registry = get_registry()

    libraries = {
        "plotly": PlotlyAdapter,
        "matplotlib": MatplotlibAdapter,
        "seaborn": SeabornAdapter,
        "d3": D3Adapter,
        "ggplot2": GGPlot2Adapter,
        "altair": AltairAdapter,
        "bokeh": BokehAdapter,
        "chartjs": ChartJSAdapter,
        "vegalite": VegaLiteAdapter,
    }

    for name, adapter_class in libraries.items():
        registry.register(name, adapter_class)

    print(f"Registered {len(libraries)}: {registry.list()}\n")

    data = {"x": [1, 2, 3, 4], "series": {"qwen": [2.1, 1.8, 2.5, 2.2],
                                          "bielik": [3.0, 2.4, 2.8, 2.6]}}
    with tempfile.TemporaryDirectory() as tmp:
        for name in libraries:
            adapter = registry.get(name)
            try:
                adapter.initialize({})
                adapter.plot(data, "line", title="Latency [s]")
                target = os.path.join(tmp, f"{name}{adapter.FORMATS[0]}")
                adapter.save(target)
                print(f"{name:11} OK      {os.path.basename(target)} "
                      f"({os.path.getsize(target)} bytes)")
            except VisualizationError as exc:
                print(f"{name:11} skipped {type(exc).__name__}: {str(exc)[:80]}")
            finally:
                adapter.shutdown()


if __name__ == "__main__":
    main()
