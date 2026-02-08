"""Example usage of visualization tool adapters."""

from code.common.visualization_tool.visualization_tool_registry import get_registry
from code.common.visualization_tool.tableau_adapter import TableauAdapter
from code.common.visualization_tool.powerbi_adapter import PowerBIAdapter
from code.common.visualization_tool.grafana_adapter import GrafanaAdapter
from code.common.visualization_tool.superset_adapter import SupersetAdapter
from code.common.visualization_tool.metabase_adapter import MetabaseAdapter

def main():
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

    print(f"Registered {len(tools)} visualization tools: {registry.list()}\n")

    for name in tools.keys():
        adapter = registry.get(name)
        adapter.connect({})
        dashboard_id = adapter.create_dashboard([1, 2, 3])
        print(f"{name}: {dashboard_id}")
        adapter.disconnect()

if __name__ == "__main__":
    main()
