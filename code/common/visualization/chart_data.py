"""
Shared data model of the visualization adapters.

``plot(data, plot_type, **kwargs)`` accepts:

- a list of numbers: y values, x = 0..n-1
- ``{"x": [...], "y": [...]}``: one series
- ``{"x": [...], "series": {"name": [...], ...}}``: several series on one x
- a list of records ``[{"x": .., "y": ..}, ...]`` (keys configurable with
  ``x=`` / ``y=`` kwargs)

``plot_type`` is one of ``line``, ``bar``, ``scatter``, ``hist`` (histogram
of the y values; ``bins=`` kwarg, default 10). Common kwargs: ``title``,
``xlabel``, ``ylabel``, ``width``, ``height``.

``normalize`` turns any of these into ``Chart`` so every adapter draws the
same thing from the same input. Invalid input raises ``VisualizationError``.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

PLOT_TYPES = ("line", "bar", "scatter", "hist")


class VisualizationError(Exception):
    """Invalid data/plot type, missing library or failed export."""


@dataclass
class Chart:  # pylint: disable=too-many-instance-attributes
    """Normalized chart description."""

    plot_type: str
    x: List[Any]
    series: Dict[str, List[float]]
    title: str = ""
    xlabel: str = ""
    ylabel: str = ""
    bins: int = 10
    width: int = 640
    height: int = 400
    options: Dict[str, Any] = field(default_factory=dict)

    def records(self) -> List[Dict[str, Any]]:
        """Long-format rows {"x", "y", "series"} (for Vega-Lite, Altair, seaborn, ggplot2)."""
        return [{"x": xv, "y": yv, "series": name}
                for name, values in self.series.items() for xv, yv in zip(self.x, values)]


def normalize(data: Any, plot_type: str, **kwargs) -> Chart:
    """Validate input and return a Chart."""
    if plot_type not in PLOT_TYPES:
        raise VisualizationError(f"plot_type must be one of {PLOT_TYPES}, got {plot_type!r}")
    x_key, y_key = kwargs.pop("x", "x"), kwargs.pop("y", "y")

    if isinstance(data, dict) and "series" in data:
        series = {str(k): list(v) for k, v in data["series"].items()}
        x = list(data.get("x") or range(max((len(v) for v in series.values()), default=0)))
    elif isinstance(data, dict):
        if y_key not in data:
            raise VisualizationError(f"data dict needs {y_key!r} (or 'series')")
        series = {str(kwargs.get("label", y_key)): list(data[y_key])}
        x = list(data.get(x_key) or range(len(data[y_key])))
    elif isinstance(data, (list, tuple)) and data and isinstance(data[0], dict):
        try:
            x = [row[x_key] for row in data]
            series = {str(kwargs.get("label", y_key)): [row[y_key] for row in data]}
        except KeyError as exc:
            raise VisualizationError(f"every record needs {exc}") from exc
    elif isinstance(data, (list, tuple)):
        series = {str(kwargs.get("label", "y")): list(data)}
        x = list(range(len(data)))
    else:
        raise VisualizationError(f"unsupported data type {type(data).__name__}")

    for name, values in series.items():
        if len(values) != len(x):
            raise VisualizationError(f"series {name!r} has {len(values)} values, x has {len(x)}")
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
            raise VisualizationError(f"series {name!r} must contain numbers only")

    known = {"title", "xlabel", "ylabel", "bins", "width", "height", "label"}
    return Chart(plot_type=plot_type, x=x, series=series,
                 title=str(kwargs.get("title", "")), xlabel=str(kwargs.get("xlabel", "")),
                 ylabel=str(kwargs.get("ylabel", "")), bins=int(kwargs.get("bins", 10)),
                 width=int(kwargs.get("width", 640)), height=int(kwargs.get("height", 400)),
                 options={k: v for k, v in kwargs.items() if k not in known})


def histogram(values: List[float], bins: int):
    """(edges, counts) with equal-width bins; stdlib only."""
    if not values:
        return [0.0, 1.0], [0]
    low, high = min(values), max(values)
    if low == high:
        high = low + 1.0
    width = (high - low) / bins
    edges = [low + i * width for i in range(bins + 1)]
    counts = [0] * bins
    for value in values:
        index = min(int((value - low) / width), bins - 1)
        counts[index] += 1
    return edges, counts


class ChartAdapterBase:
    """Lifecycle shared by the visualization adapters (mixed into each adapter).

    Subclasses implement ``draw(chart) -> figure`` and
    ``export(figure, output_path, extension)`` and list the extensions they
    can write in ``FORMATS``. Configuration passed to ``initialize`` becomes
    the default kwargs of every ``plot`` call (e.g. ``{"width": 800}``).
    """

    LIBRARY = "library"
    FORMATS: tuple = ()

    def __init__(self):
        self.initialized = False
        self.figure = None
        self.chart = None
        self.defaults: Dict[str, Any] = {}

    def initialize(self, config: Dict[str, Any]) -> None:
        """Keep default plot options; ``_setup`` imports the library."""
        self.defaults = dict(config or {})
        self._setup()
        self.initialized = True

    def plot(self, data: Any, plot_type: str, **kwargs) -> Any:
        """Draw the chart and return the library's figure object."""
        if not self.initialized:
            raise VisualizationError(f"{type(self).__name__} is not initialized")
        self.chart = normalize(data, plot_type, **{**self.defaults, **kwargs})
        self.figure = self.draw(self.chart)
        return self.figure

    def save(self, output_path: str) -> None:
        """Write the last figure; the format follows the extension."""
        if self.figure is None:
            raise VisualizationError("nothing to save - call plot() first")
        extension = output_path.rsplit(".", 1)[-1].lower() if "." in output_path else ""
        if f".{extension}" not in self.FORMATS:
            raise VisualizationError(
                f"{type(self).__name__} writes {self.FORMATS}, not {extension!r}")
        self.export(self.figure, output_path, extension)

    def shutdown(self) -> None:
        """Release the figure."""
        self._release()
        self.initialized = False
        self.figure = None
        self.chart = None

    # -- hooks ---------------------------------------------------------------

    def _setup(self) -> None:
        """Import the library (default: nothing to import)."""

    def _release(self) -> None:
        """Free library resources (default: nothing)."""

    def draw(self, chart: Chart) -> Any:
        """Build the figure."""
        raise NotImplementedError

    def export(self, figure: Any, output_path: str, extension: str) -> None:
        """Write the figure."""
        raise NotImplementedError
