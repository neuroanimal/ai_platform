"""Tests of the visualization adapters.

Matplotlib, seaborn and Plotly render for real (files are opened and
checked); Vega-Lite and Chart.js specs are checked structurally; generated
D3 code is syntax-checked with node when available; ggplot2 is checked
through a recording runner (R is not installed). Altair and Bokeh are
skipped when their packages are absent.
"""

import importlib.util
import json
import shutil
import subprocess

import pytest

from ai_platform.common.util.cli_runner import ToolResult
from ai_platform.common.visualization.altair_adapter import AltairAdapter
from ai_platform.common.visualization.bokeh_adapter import BokehAdapter
from ai_platform.common.visualization.chart_data import VisualizationError, histogram, normalize
from ai_platform.common.visualization.chartjs_adapter import ChartJSAdapter
from ai_platform.common.visualization.d3_adapter import D3Adapter
from ai_platform.common.visualization.ggplot2_adapter import GGPlot2Adapter
from ai_platform.common.visualization.matplotlib_adapter import MatplotlibAdapter
from ai_platform.common.visualization.plotly_adapter import PlotlyAdapter
from ai_platform.common.visualization.seaborn_adapter import SeabornAdapter
from ai_platform.common.visualization.vegalite_adapter import VegaLiteAdapter

SERIES = {"x": [1, 2, 3, 4], "series": {"qwen": [2.1, 1.8, 2.5, 2.2], "bielik": [3.0, 2.4, 2.8, 2.6]}}
TYPES = ["line", "bar", "scatter", "hist"]


def test_normalize_forms():
    assert normalize([3, 1, 2], "line").x == [0, 1, 2]
    chart = normalize([{"t": "a", "v": 1}, {"t": "b", "v": 2}], "bar", x="t", y="v")
    assert chart.x == ["a", "b"] and chart.series == {"v": [1, 2]}
    assert len(normalize(SERIES, "line").records()) == 8
    with pytest.raises(VisualizationError):
        normalize([1, 2], "pie")
    with pytest.raises(VisualizationError):
        normalize({"x": [1, 2], "y": [1]}, "line")
    with pytest.raises(VisualizationError):
        normalize({"y": ["a"]}, "line")


def test_histogram_counts():
    edges, counts = histogram([1, 2, 2, 3, 10], 3)
    assert sum(counts) == 5 and len(edges) == 4 and counts[0] == 4


@pytest.mark.parametrize("plot_type", TYPES)
@pytest.mark.parametrize("cls", [MatplotlibAdapter, SeabornAdapter])
def test_raster_backends_write_real_images(cls, plot_type, tmp_path):
    from PIL import Image  # pylint: disable=import-outside-toplevel
    adapter = cls()
    adapter.initialize({"width": 400, "height": 300})
    adapter.plot(SERIES, plot_type, title="Czas odpowiedzi", xlabel="run", ylabel="s")
    out = tmp_path / f"{plot_type}.png"
    adapter.save(str(out))
    with Image.open(out) as image:
        assert image.size == (400, 300)
    adapter.save(str(tmp_path / f"{plot_type}.svg"))
    assert "<svg" in (tmp_path / f"{plot_type}.svg").read_text(encoding="utf-8")[:500]
    with pytest.raises(VisualizationError):
        adapter.save(str(tmp_path / "x.html"))


@pytest.mark.parametrize("plot_type", TYPES)
def test_plotly_html_and_json(plot_type, tmp_path):
    adapter = PlotlyAdapter()
    adapter.initialize({})
    figure = adapter.plot(SERIES, plot_type, title="T")
    assert len(figure.data) == 2
    adapter.save(str(tmp_path / "c.html"))
    assert "cdn.plot.ly" in (tmp_path / "c.html").read_text(encoding="utf-8")
    adapter.save(str(tmp_path / "c.json"))
    assert json.loads((tmp_path / "c.json").read_text())["layout"]["title"]["text"] == "T"


@pytest.mark.parametrize("plot_type", TYPES)
def test_vegalite_spec(plot_type, tmp_path):
    adapter = VegaLiteAdapter()
    adapter.initialize({})
    spec = adapter.plot(SERIES, plot_type)
    assert spec["$schema"].endswith("v5.json")
    assert len(spec["data"]["values"]) == 8
    assert spec["encoding"]["color"]["field"] == "series"
    adapter.save(str(tmp_path / "c.html"))
    assert "vegaEmbed" in (tmp_path / "c.html").read_text(encoding="utf-8")


@pytest.mark.parametrize("plot_type", TYPES)
def test_chartjs_config(plot_type, tmp_path):
    adapter = ChartJSAdapter()
    adapter.initialize({})
    config = adapter.plot(SERIES, plot_type, title="T")
    assert config["type"] in ("line", "bar", "scatter")
    assert len(config["data"]["datasets"]) == 2
    if plot_type == "hist":
        assert sum(config["data"]["datasets"][0]["data"]) == 4
    adapter.save(str(tmp_path / "c.html"))
    assert "chart.js@4" in (tmp_path / "c.html").read_text(encoding="utf-8")


@pytest.mark.parametrize("plot_type", TYPES)
def test_d3_script_syntax(plot_type, tmp_path):
    adapter = D3Adapter()
    adapter.initialize({})
    script = adapter.plot(SERIES, plot_type, title='a "quoted" title')
    assert '"a \\"quoted\\" title"' in script
    node = shutil.which("node")
    if node:
        path = tmp_path / "c.js"
        adapter.save(str(path))
        check = subprocess.run([node, "--check", str(path)], capture_output=True,
                               text=True, check=False)
        assert check.returncode == 0, check.stderr


def test_ggplot2_script_and_command(tmp_path):
    calls = []

    def runner(command, **kwargs):
        calls.append((list(command), open(command[1], encoding="utf-8").read(), kwargs))
        return ToolResult(command, 0, "", "")

    adapter = GGPlot2Adapter()
    adapter.initialize({"executable": "Rscript", "runner": runner})
    script = adapter.plot(SERIES, "bar", title='Tytuł "x"')
    assert 'geom_col(position = "dodge")' in script
    assert 'labs(title = "Tytuł \\"x\\""' in script
    adapter.save(str(tmp_path / "c.png"))
    command, written, _ = calls[0]
    assert command[0] == "Rscript" and command[1].endswith("chart.R")
    assert f'ggsave("{tmp_path / "c.png"}", p' in written


@pytest.mark.skipif(not importlib.util.find_spec("altair"), reason="altair not installed")
def test_altair(tmp_path):
    adapter = AltairAdapter()
    adapter.initialize({})
    adapter.plot(SERIES, "line")
    adapter.save(str(tmp_path / "c.html"))


@pytest.mark.skipif(not importlib.util.find_spec("bokeh"), reason="bokeh not installed")
def test_bokeh(tmp_path):
    adapter = BokehAdapter()
    adapter.initialize({})
    adapter.plot(SERIES, "bar")
    adapter.save(str(tmp_path / "c.html"))


def test_missing_library_is_reported():
    if importlib.util.find_spec("bokeh"):
        pytest.skip("bokeh installed")
    with pytest.raises(VisualizationError, match="pip install bokeh"):
        BokehAdapter().initialize({})


def test_save_before_plot():
    adapter = VegaLiteAdapter()
    adapter.initialize({})
    with pytest.raises(VisualizationError, match="plot"):
        adapter.save("x.json")
