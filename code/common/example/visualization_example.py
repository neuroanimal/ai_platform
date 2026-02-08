"""Example usage of visualization library adapters."""

from code.common.visualization.visualization_registry import get_registry
from code.common.visualization.plotly_adapter import PlotlyAdapter
from code.common.visualization.matplotlib_adapter import MatplotlibAdapter
from code.common.visualization.seaborn_adapter import SeabornAdapter
from code.common.visualization.d3_adapter import D3Adapter
from code.common.visualization.ggplot2_adapter import GGPlot2Adapter
from code.common.visualization.altair_adapter import AltairAdapter
from code.common.visualization.bokeh_adapter import BokehAdapter
from code.common.visualization.chartjs_adapter import ChartJSAdapter
from code.common.visualization.vegalite_adapter import VegaLiteAdapter

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
