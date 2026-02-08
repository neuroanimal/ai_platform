"""Example usage of scientific computing tool adapters."""

from ai_platform.common.scientific_tool.scientific_tool_registry import get_registry
from ai_platform.common.scientific_tool.matlab_adapter import MATLABAdapter
from ai_platform.common.scientific_tool.mathcad_adapter import MathCADAdapter
from ai_platform.common.scientific_tool.octave_adapter import OctaveAdapter
from ai_platform.common.scientific_tool.mathematica_adapter import MathematicaAdapter
from ai_platform.common.scientific_tool.sagemath_adapter import SageMathAdapter

def main():
    registry = get_registry()

    tools = {
        "matlab": MATLABAdapter,
        "mathcad": MathCADAdapter,
        "octave": OctaveAdapter,
        "mathematica": MathematicaAdapter,
        "sagemath": SageMathAdapter,
    }

    for name, adapter_class in tools.items():
        registry.register(name, adapter_class)

    print(f"Registered {len(tools)} scientific tools: {registry.list()}\n")

    for name in tools.keys():
        adapter = registry.get(name)
        adapter.connect({})
        result = adapter.execute("x = 2 + 2")
        print(f"{result['tool']}: OK")
        adapter.disconnect()

if __name__ == "__main__":
    main()
