"""Example usage of visualization library adapters."""

from ai_platform.common.visualization.visualization_registry import get_registry
from ai_platform.common.visualization.plotly_adapter import PlotlyAdapter
from ai_platform.common.visualization.matplotlib_adapter import MatplotlibAdapter
from ai_platform.common.visualization.seaborn_adapter import SeabornAdapter
from ai_platform.common.visualization.d3_adapter import D3Adapter
from ai_platform.common.visualization.ggplot2_adapter import GGPlot2Adapter
from ai_platform.common.visualization.altair_adapter import AltairAdapter
from ai_platform.common.visualization.bokeh_adapter import BokehAdapter
from ai_platform.common.visualization.chartjs_adapter import ChartJSAdapter
from ai_platform.common.visualization.vegalite_adapter import VegaLiteAdapter

def main():
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

    print(f"Registered {len(libraries)} visualization libraries: {registry.list()}\n")

    for name in libraries.keys():
        adapter = registry.get(name)
        adapter.initialize({})
        result = adapter.plot([1, 2, 3], "line")
        print(f"{result['library']}: OK")
        adapter.shutdown()

if __name__ == "__main__":
    main()
