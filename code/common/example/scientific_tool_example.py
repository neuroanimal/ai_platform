"""Example usage of scientific tool adapters.

Registers every adapter and exercises each one with a small, real
operation (computing 17 * 23). Nothing is fabricated: an adapter whose tool, server or
package is not available here is reported as skipped with the reason.

    python -m ai_platform.common.example.scientific_tool_example
"""

# Examples follow the same register-and-try pattern on purpose.
# pylint: disable=duplicate-code

from ai_platform.common.scientific_tool.mathcad_adapter import MathCADAdapter
from ai_platform.common.scientific_tool.mathematica_adapter import MathematicaAdapter
from ai_platform.common.scientific_tool.matlab_adapter import MATLABAdapter
from ai_platform.common.scientific_tool.octave_adapter import OctaveAdapter
from ai_platform.common.scientific_tool.sagemath_adapter import SageMathAdapter
from ai_platform.common.scientific_tool.scientific_tool_registry import get_registry
from ai_platform.common.scientific_tool.script_tool_support import ScientificToolError


def main():
    """Register all adapters and exercise the usable ones."""
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

    print(f"Registered {len(tools)}: {registry.list()}\n")

    scripts = {"octave": "disp(17*23)", "matlab": "disp(17*23)", "sagemath": "print(17*23)",
               "mathematica": "Print[17*23]", "mathcad": "17*23"}
    for name in tools:
        adapter = registry.get(name)
        try:
            adapter.connect({})
            print(f"{name:12} OK      {adapter.execute(scripts[name])}")
        except (ScientificToolError, NotImplementedError) as exc:
            print(f"{name:12} skipped {type(exc).__name__}: {str(exc)[:80]}")
        finally:
            adapter.disconnect()


if __name__ == "__main__":
    main()
