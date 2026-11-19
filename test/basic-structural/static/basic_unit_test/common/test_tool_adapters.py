"""Tests of the adapters that drive external programs or generate code.

None of LaTeX, Inkscape, ImageMagick, GIMP, Dia, FFmpeg, VLC, Octave,
MATLAB, SageMath or Wolfram is installed in the development environment,
so their adapters are checked through a recording ``runner``: the test
asserts the exact command line and, where it matters, simulates the
output file. Real execution is covered where the environment allows:
Pillow, the native SVG writer, ``node --check`` on generated JavaScript,
and the shared runner itself (with python3 standing in for SageMath's
``-c`` interface).
"""

import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

from ai_platform.common.image_tool.dia_adapter import DiaAdapter
from ai_platform.common.image_tool.gimp_adapter import GIMPAdapter, scheme_string
from ai_platform.common.image_tool.image_operations import ImageToolError
from ai_platform.common.image_tool.imagemagick_adapter import ImageMagickAdapter
from ai_platform.common.image_tool.inkscape_tool_adapter import InkscapeToolAdapter
from ai_platform.common.image_tool.pillow_image_adapter import PillowImageAdapter
from ai_platform.common.latex.asymptote_adapter import AsymptoteAdapter
from ai_platform.common.latex.circuitikz_adapter import CircuiTikZAdapter
from ai_platform.common.latex.latex_toolchain_support import LaTeXError
from ai_platform.common.latex.metapost_adapter import MetaPostAdapter
from ai_platform.common.latex.pgfplots_adapter import PGFPlotsAdapter
from ai_platform.common.latex.tikz_adapter import TikZAdapter
from ai_platform.common.scientific_tool.mathcad_adapter import MathCADAdapter
from ai_platform.common.scientific_tool.matlab_adapter import MATLABAdapter
from ai_platform.common.scientific_tool.octave_adapter import OctaveAdapter
from ai_platform.common.scientific_tool.sagemath_adapter import SageMathAdapter
from ai_platform.common.scientific_tool.script_tool_support import ScientificToolError
from ai_platform.common.svg.inkscape_adapter import InkscapeAdapter
from ai_platform.common.svg.native_svg_adapter import NativeSVGAdapter
from ai_platform.common.svg.raphael_adapter import RaphaelAdapter
from ai_platform.common.svg.snapsvg_adapter import SnapSVGAdapter
from ai_platform.common.svg.svg_support import SVGError
from ai_platform.common.svg.svgjs_adapter import SVGJSAdapter
from ai_platform.common.util.cli_runner import ToolNotFoundError, ToolResult, run_tool
from ai_platform.common.video_tool.ffmpeg_adapter import FFmpegAdapter
from ai_platform.common.video_tool.video_operations import VideoToolError
from ai_platform.common.video_tool.virtualdub_adapter import VirtualDubAdapter
from ai_platform.common.video_tool.vlc_adapter import VLCAdapter

ELEMENTS = [
    {"type": "rect", "x": 10, "y": 10, "width": 80, "height": 40, "fill": "#36c"},
    {"type": "circle", "cx": 50, "cy": 50, "r": 20, "stroke": "black"},
    {"type": "line", "x1": 0, "y1": 0, "x2": 100, "y2": 100},
    {"type": "polygon", "points": [[0, 0], [10, 20], [20, 0]]},
    {"type": "text", "x": 5, "y": 15, "text": "a < b & \"c\"", "font-size": 12},
]


class Recorder:
    """Stand-in for run_tool: records commands, optionally creates a file."""

    def __init__(self, create=None):
        self.commands = []
        self.kwargs = []
        self.create = create

    def __call__(self, command, **kwargs):
        self.commands.append(list(command))
        self.kwargs.append(kwargs)
        if self.create:
            self.create(command, kwargs)
        return ToolResult(command, 0, "out\n", "")


# ----------------------------------------------------------------------------
# shared runner
# ----------------------------------------------------------------------------

def test_run_tool_no_shell_and_errors(tmp_path):
    marker = tmp_path / "x; touch pwned"
    result = run_tool([sys.executable, "-c", "import sys; print(sys.argv[1])", str(marker)])
    assert result.stdout.strip() == str(marker)
    assert not (tmp_path / "pwned").exists()
    with pytest.raises(ToolNotFoundError):
        run_tool(["definitely-not-a-tool-xyz"])


def test_sagemath_shape_runs_for_real_with_python_standing_in():
    tool = SageMathAdapter()
    tool.connect({"executable": sys.executable})
    assert tool.execute("print(17 * 23)") == "391"
    with pytest.raises(ScientificToolError, match="exit status"):
        tool.execute("raise SystemExit(3)")


@pytest.mark.parametrize("cls,expected", [
    (OctaveAdapter, ["octave", "--quiet", "--no-window-system", "--eval", "disp(1)"]),
    (MATLABAdapter, ["matlab", "-batch", "disp(1)"]),
])
def test_scientific_commands(cls, expected):
    runner = Recorder()
    tool = cls()
    tool.connect({"executable": expected[0], "runner": runner})
    assert tool.execute("disp(1)") == "out"
    assert runner.commands == [expected]


def test_scientific_missing_tool_and_mathcad(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    with pytest.raises(ScientificToolError, match="not found"):
        OctaveAdapter().connect({"runner": Recorder()})
    with pytest.raises(NotImplementedError, match="COM"):
        MathCADAdapter().execute("x")


# ----------------------------------------------------------------------------
# LaTeX family
# ----------------------------------------------------------------------------

def test_tikz_render_is_a_complete_document():
    tikz = TikZAdapter()
    tikz.initialize({"packages": ["amsmath"]})
    doc = tikz.render(r"\draw (0,0) -- (1,1);", options="scale=2")
    assert doc.startswith(r"\documentclass[border=2pt]{standalone}")
    assert r"\usepackage{tikz}" in doc and r"\usepackage{amsmath}" in doc
    assert "\\begin{tikzpicture}[scale=2]\n\\draw (0,0) -- (1,1);\n\\end{tikzpicture}" in doc


def test_pgfplots_and_circuitikz_wrappers():
    plots = PGFPlotsAdapter()
    plots.initialize({})
    doc = plots.render(r"\addplot {x^2};", options="xlabel=$x$")
    assert r"\pgfplotsset{compat=1.18}" in doc and r"\begin{axis}[xlabel=$x$]" in doc
    circuit = CircuiTikZAdapter()
    circuit.initialize({})
    assert r"\begin{circuitikz}" in circuit.render(r"\draw (0,0) to[R] (2,0);")


def test_latex_compile_command_and_copy(tmp_path, monkeypatch):
    def fake_latex(command, kwargs):
        with open(os.path.join(kwargs["cwd"], "doc.pdf"), "wb") as handle:
            handle.write(b"%PDF-1.5 fake")

    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}" if name == "pdflatex" else None)
    runner = Recorder(create=fake_latex)
    tikz = TikZAdapter()
    tikz.initialize({"runner": runner})
    target = tmp_path / "out" / "fig.pdf"
    tikz.compile(r"\draw (0,0) circle (1);", str(target))
    assert runner.commands[0] == ["/usr/bin/pdflatex", "-interaction=nonstopmode",
                                  "-halt-on-error", "doc.tex"]
    assert target.read_bytes().startswith(b"%PDF")
    with pytest.raises(LaTeXError):
        tikz.compile("x", str(tmp_path / "fig.png"))


def test_latex_missing_toolchain_is_reported(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    tikz = TikZAdapter()
    tikz.initialize({})
    with pytest.raises(LaTeXError, match="TeX"):
        tikz.compile("x", "/tmp/never.pdf")


def test_asymptote_and_metapost(tmp_path, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")

    def produce(names):
        def create(command, kwargs):
            for name in names:
                open(os.path.join(kwargs["cwd"], name), "w", encoding="utf-8").close()
        return create

    asy_runner = Recorder(create=produce(["doc.svg"]))
    asy = AsymptoteAdapter()
    asy.initialize({"runner": asy_runner})
    assert asy.render("draw((0,0)--(1,1));").startswith("size(6cm);")
    asy.compile("draw((0,0)--(1,1));", str(tmp_path / "a.svg"))
    assert asy_runner.commands[0] == ["/usr/bin/asy", "-f", "svg", "-o", "doc", "doc.asy"]

    mp_runner = Recorder(create=produce(["doc-1.svg"]))
    mpost = MetaPostAdapter()
    mpost.initialize({"runner": mp_runner})
    assert 'outputformat := "svg";' in mpost.render("draw (0,0)--(10,10);")
    mpost.compile("draw (0,0)--(10,10);", str(tmp_path / "m.svg"))
    assert (tmp_path / "m.svg").exists()


# ----------------------------------------------------------------------------
# SVG family
# ----------------------------------------------------------------------------

def test_native_svg_is_valid_and_escaped(tmp_path):
    svg = NativeSVGAdapter()
    svg.initialize({"width": 120, "height": 120})
    markup = svg.create(ELEMENTS)
    root = ET.fromstring(markup)
    assert root.tag.endswith("svg") and root.get("width") == "120"
    texts = [e.text for e in root.iter() if e.tag.endswith("text")]
    assert texts == ['a < b & "c"']
    assert root.find("{http://www.w3.org/2000/svg}polygon").get("points") == "0,0 10,20 20,0"
    path = tmp_path / "d.svg"
    svg.save(markup, str(path))
    ET.parse(path)


def test_svg_rejects_unknown_elements():
    svg = NativeSVGAdapter()
    svg.initialize({})
    with pytest.raises(SVGError):
        svg.create([{"type": "star"}])


def test_inkscape_svg_export_command(tmp_path, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/inkscape")
    runner = Recorder()
    ink = InkscapeAdapter()
    ink.initialize({"runner": runner, "dpi": 150})
    ink.save(ink.create(ELEMENTS), str(tmp_path / "d.png"))
    command = runner.commands[0]
    assert command[0] == "/usr/bin/inkscape" and command[1].endswith("drawing.svg")
    assert command[2:] == [f"--export-filename={tmp_path / 'd.png'}", "--export-dpi=150"]
    ink.save("<svg/>", str(tmp_path / "plain.svg"))
    assert (tmp_path / "plain.svg").read_text() == "<svg/>"


@pytest.mark.parametrize("cls", [RaphaelAdapter, SnapSVGAdapter, SVGJSAdapter])
def test_javascript_svg_generators(cls, tmp_path):
    adapter = cls()
    adapter.initialize({"container_id": "c1"})
    script = adapter.create(ELEMENTS, width=120, height=80)
    assert script.startswith("var paper")
    assert '"a < b & \\"c\\""' in script  # label embedded as a JSON string literal
    html = tmp_path / "d.html"
    adapter.save(script, str(html))
    page = html.read_text(encoding="utf-8")
    assert adapter.LIBRARY_URL in page and 'id="c1"' in page
    with pytest.raises(SVGError):
        adapter.save(script, str(tmp_path / "d.svg"))
    node = shutil.which("node")
    if node:
        js_file = tmp_path / "d.js"
        adapter.save(script, str(js_file))
        check = subprocess.run([node, "--check", str(js_file)], capture_output=True,
                               text=True, check=False)
        assert check.returncode == 0, check.stderr


# ----------------------------------------------------------------------------
# image tools
# ----------------------------------------------------------------------------

@pytest.fixture(name="png")
def fixture_png(tmp_path):
    """A 40x20 RGBA test image."""
    from PIL import Image  # pylint: disable=import-outside-toplevel
    path = tmp_path / "in.png"
    Image.new("RGBA", (40, 20), (255, 0, 0, 255)).save(path)
    return str(path)


def test_pillow_operations_for_real(png, tmp_path):
    from PIL import Image  # pylint: disable=import-outside-toplevel
    tool = PillowImageAdapter()
    tool.connect({})
    out = tool.process(png, {"crop": [0, 0, 20, 10], "resize": "200%", "rotate": 90,
                             "grayscale": True, "output": str(tmp_path / "o.jpg"),
                             "quality": 80})
    with Image.open(out) as image:
        assert image.size == (20, 40) and image.mode == "L" and image.format == "JPEG"
    assert tool.process(png, {"flip": "horizontal"}).endswith("in_processed.png")
    with pytest.raises(ImageToolError, match="unsupported"):
        tool.process(png, {"sharpen": 1})
    with pytest.raises(ImageToolError, match="not found"):
        tool.process(str(tmp_path / "missing.png"), {})


def test_imagemagick_command(png):
    runner = Recorder()
    tool = ImageMagickAdapter()
    tool.connect({"executable": "magick", "runner": runner})
    out = tool.process(png, {"crop": [1, 2, 30, 10], "resize": [64, 32], "rotate": 90,
                             "flip": "horizontal", "grayscale": True, "blur": 1.5,
                             "format": "jpg", "quality": 85})
    assert runner.commands[0] == [
        "magick", png, "-crop", "30x10+1+2", "+repage", "-resize", "64x32!", "-rotate", "90.0",
        "-flop", "-colorspace", "Gray", "-blur", "0x1.5", "-quality", "85", out]
    assert out.endswith("in_processed.jpg")


def test_inkscape_tool_and_dia_commands(tmp_path):
    svg = tmp_path / "d.svg"
    svg.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
    runner = Recorder()
    ink = InkscapeToolAdapter()
    ink.connect({"executable": "inkscape", "runner": runner})
    out = ink.process(str(svg), {"width": 800, "area": "drawing", "background": "#fff"})
    assert runner.commands[0] == ["inkscape", str(svg), f"--export-filename={out}",
                                  "--export-area-drawing", "--export-width=800",
                                  "--export-background=#fff"]
    dia_file = tmp_path / "d.dia"
    dia_file.write_text("x", encoding="utf-8")
    dia = DiaAdapter()
    dia.connect({"executable": "dia", "runner": runner})
    out = dia.process(str(dia_file), {"format": "svg", "width": 640})
    assert runner.commands[1] == ["dia", "--nosplash", f"--export={out}", "--filter=svg",
                                  "--size=640x", str(dia_file)]


def test_gimp_script_and_escaping(png):
    runner = Recorder()
    gimp = GIMPAdapter()
    gimp.connect({"executable": "gimp-console", "runner": runner})
    gimp.process(png, {"resize": "50%", "rotate": 90, "grayscale": True, "flip": "vertical"})
    command = runner.commands[0]
    assert command[:3] == ["gimp-console", "-i", "-b"] and command[-2:] == ["-b", "(gimp-quit 0)"]
    script = command[3]
    assert "(gimp-image-rotate image ROTATE-90)" in script
    assert "(gimp-image-flip image ORIENTATION-VERTICAL)" in script
    assert script.count("(") == script.count(")")
    assert scheme_string('a"b\\c') == '"a\\"b\\\\c"'
    with pytest.raises(ImageToolError, match="90, 180 or 270"):
        gimp.process(png, {"rotate": 45})


# ----------------------------------------------------------------------------
# video tools
# ----------------------------------------------------------------------------

@pytest.fixture(name="video")
def fixture_video(tmp_path):
    """An existing (dummy) input file."""
    path = tmp_path / "in.mp4"
    path.write_bytes(b"not really a video")
    return str(path)


def test_ffmpeg_command(video):
    runner = Recorder()
    tool = FFmpegAdapter()
    tool.connect({"executable": "ffmpeg", "runner": runner})
    out = tool.process(video, {"trim": [5, 10], "scale": [640, -2], "fps": 25,
                               "video_codec": "libx264", "crf": 23, "mute": True})
    assert runner.commands[0] == [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", "5.0", "-i", video,
        "-t", "10.0", "-vf", "scale=640:-2,fps=25", "-c:v", "libx264", "-crf", "23", "-an", out]
    audio = tool.process(video, {"extract_audio": True, "audio_codec": "aac"})
    assert audio.endswith("in_processed.m4a")
    assert runner.commands[1][-4:] == ["-vn", "-c:a", "aac", audio]
    with pytest.raises(VideoToolError, match="contradict"):
        tool.process(video, {"mute": True, "extract_audio": True})


def test_vlc_command(video, tmp_path):
    runner = Recorder()
    tool = VLCAdapter()
    tool.connect({"executable": "cvlc", "runner": runner})
    out = str(tmp_path / "o.mp4")
    tool.process(video, {"trim": [5, 10], "scale": [640, 0], "fps": 25, "output": out})
    assert runner.commands[0] == [
        "cvlc", "-q", "-I", "dummy", video, "--start-time=5", "--stop-time=15", "--sout",
        f"#transcode{{vcodec=h264,acodec=mp4a,width=640,fps=25}}:std{{access=file,mux=mp4,dst='{out}'}}",
        "vlc://quit"]
    with pytest.raises(NotImplementedError, match="FFmpegAdapter"):
        VirtualDubAdapter().process(video, {})
