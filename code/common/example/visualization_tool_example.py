"""Example usage of dashboard tool adapters.

Registers every adapter and exercises each one with a small, real operation
against the tools' default local URLs. Nothing is fabricated: an adapter whose
tool, server or package is not available here is reported as skipped with the
reason.

    python -m ai_platform.common.example.visualization_tool_example
"""

# Examples follow the same register-and-try pattern on purpose.
# pylint: disable=duplicate-code

from ai_platform.common.visualization_tool.dashboard_support import DashboardToolError
from ai_platform.common.visualization_tool.grafana_adapter import GrafanaAdapter
from ai_platform.common.visualization_tool.metabase_adapter import MetabaseAdapter
from ai_platform.common.visualization_tool.powerbi_adapter import PowerBIAdapter
from ai_platform.common.visualization_tool.superset_adapter import SupersetAdapter
from ai_platform.common.visualization_tool.tableau_adapter import TableauAdapter
from ai_platform.common.visualization_tool.visualization_tool_registry import get_registry


def main():
    """Register all adapters and exercise the usable ones."""
    registry = get_registry()

    tools = {
        "tableau": TableauAdapter,
        "powerbi": PowerBIAdapter,
        "grafana": GrafanaAdapter,
        "superset": SupersetAdapter,
        "metabase": MetabaseAdapter,
    }

    for name, adapter_class in tools.items():
        registry.register(name, adapter_class)

    print(f"Registered {len(tools)}: {registry.list()}\n")

    data = {"x": ["r1", "r2"], "series": {"qwen": [2.1, 1.8]}}
    for name in tools:
        adapter = registry.get(name)
        try:
            adapter.connect({})
            print(f"{name:9} OK      {adapter.create_dashboard(data, title='Example')}")
        except (DashboardToolError, NotImplementedError) as exc:
            print(f"{name:9} skipped {type(exc).__name__}: {str(exc)[:80]}")
        finally:
            adapter.disconnect()


if __name__ == "__main__":
    main()
