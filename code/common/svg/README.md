# SVG Support

SVG creation and manipulation adapters.

## Supported Tools

- **svgwrite**: Python SVG library
- **Snap.svg**: JavaScript SVG library
- **SVG.js**: Lightweight SVG library
- **Raphael**: Cross-browser SVG library
- **Inkscape**: Professional vector graphics

## Usage

```python
from code.common.svg.svg_registry import get_registry
from code.common.svg.svgwrite_adapter import SvgwriteAdapter

registry = get_registry()
registry.register("svgwrite", SvgwriteAdapter)

svg = registry.get("svgwrite")
svg.initialize({})
content = svg.create('<rect width="100" height="100"/>')
svg.save(content, "output.svg")
svg.shutdown()
```
