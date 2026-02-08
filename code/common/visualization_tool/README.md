# Visualization Tool Support

Interactive dashboard and BI tool adapters.

## Supported Tools

- **Tableau**: Enterprise BI platform
- **Power BI**: Microsoft BI tool
- **Grafana**: Observability dashboards
- **Apache Superset**: Open-source BI
- **Metabase**: Simple BI tool

## Usage

```python
from code.common.visualization_tool.visualization_tool_registry import get_registry
from code.common.visualization_tool.grafana_adapter import GrafanaAdapter

registry = get_registry()
registry.register("grafana", GrafanaAdapter)

tool = registry.get("grafana")
tool.connect({"url": "http://localhost:3000"})
dashboard_id = tool.create_dashboard(data)
tool.disconnect()
```
