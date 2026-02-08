# Visualization Library Support

Data visualization library adapters.

## Supported Libraries

### Python
- **Plotly**: Interactive plots
- **Matplotlib**: Static plots
- **Seaborn**: Statistical visualization
- **Altair**: Declarative visualization
- **Bokeh**: Interactive web plots

### JavaScript
- **D3.js**: Data-driven documents
- **Chart.js**: Simple charts
- **Vega-Lite**: Grammar of graphics

### R
- **ggplot2**: Grammar of graphics

## Usage

```python
from code.common.visualization.visualization_registry import get_registry
from code.common.visualization.plotly_adapter import PlotlyAdapter

registry = get_registry()
registry.register("plotly", PlotlyAdapter)

viz = registry.get("plotly")
viz.initialize({})
fig = viz.plot([1, 2, 3], "line")
viz.save("output.html")
viz.shutdown()
```
