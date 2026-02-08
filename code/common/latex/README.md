# LaTeX/TeX Support

LaTeX and TeX-based graphics adapters.

## Supported Tools

- **TikZ**: Powerful graphics language
- **PGF**: Portable Graphics Format
- **PGFPlots**: Publication-quality plots
- **Asymptote**: Vector graphics language
- **MetaPost**: Graphics programming language
- **CircuiTikZ**: Circuit diagrams

## Usage

```python
from code.common.latex.latex_registry import get_registry
from code.common.latex.tikz_adapter import TikZAdapter

registry = get_registry()
registry.register("tikz", TikZAdapter)

latex = registry.get("tikz")
latex.initialize({})
code = latex.render("\\draw (0,0) circle (1cm);")
latex.compile(code, "output.pdf")
latex.shutdown()
```
