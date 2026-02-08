"""Example usage of LaTeX/TeX adapters."""

from ai_platform.common.latex.latex_registry import get_registry
from ai_platform.common.latex.tikz_adapter import TikZAdapter
from ai_platform.common.latex.pgf_adapter import PGFAdapter
from ai_platform.common.latex.pgfplots_adapter import PGFPlotsAdapter
from ai_platform.common.latex.asymptote_adapter import AsymptoteAdapter
from ai_platform.common.latex.metapost_adapter import MetaPostAdapter
from ai_platform.common.latex.circuitikz_adapter import CircuiTikZAdapter

def main():
    registry = get_registry()

    tools = {
        "tikz": TikZAdapter,
        "pgf": PGFAdapter,
        "pgfplots": PGFPlotsAdapter,
        "asymptote": AsymptoteAdapter,
        "metapost": MetaPostAdapter,
        "circuitikz": CircuiTikZAdapter,
    }

    for name, adapter_class in tools.items():
        registry.register(name, adapter_class)

    print(f"Registered {len(tools)} LaTeX tools: {registry.list()}\n")

    for name in tools.keys():
        adapter = registry.get(name)
        adapter.initialize({})
        result = adapter.render("\\draw (0,0) -- (1,1);")
        print(f"{name}: {result[:50]}...")
        adapter.shutdown()

if __name__ == "__main__":
    main()
