"""GIMP adapter (GIMP 2.10 batch mode, Script-Fu).

Builds a Script-Fu program for the operations and runs GIMP headless::

    gimp -i -b '<script>' -b '(gimp-quit 0)'

Operations: ``crop``, ``resize`` ([w, h] or "N%"), ``rotate`` (90, 180 or
270 - GIMP's lossless rotation), ``flip``, ``grayscale``, ``blur`` (Gaussian
radius in px), ``format``, ``output``.

File paths are embedded as Scheme string literals with ``\\`` and ``"``
escaped. Targets the GIMP 2.10 procedure database (``gimp-image-get-active-
layer``, ``gimp-file-save`` ...); GIMP 3 renamed several procedures, so a
GIMP 3 installation needs a separate script. Not verified against an
installed GIMP here; unit tests check the generated script.

Configuration: ``timeout`` (default 300), ``runner`` (tests).
Previously a stub that returned a fake path; the class name and the
ImageToolAdapter methods are unchanged.
"""

# The CLI adapters share their connect/process skeleton by design.
# pylint: disable=duplicate-code

from typing import Any, Dict, List

from ai_platform.common.image_tool.base import ImageToolAdapter
from ai_platform.common.image_tool.image_operations import (
    ImageToolError,
    check_operations,
    output_path,
    require_input,
)
from ai_platform.common.util.cli_runner import CLIToolMixin

SUPPORTED = ("crop", "resize", "rotate", "flip", "grayscale", "blur")
_ROTATIONS = {90: "ROTATE-90", 180: "ROTATE-180", 270: "ROTATE-270"}


def scheme_string(text: str) -> str:
    """Scheme string literal."""
    return '"' + str(text).replace("\\", "\\\\").replace('"', '\\"') + '"'


def script_fu(input_path: str, target: str, operations: Dict[str, Any]) -> str:
    """Script-Fu program applying the operations in order."""
    steps: List[str] = []
    for name, value in operations.items():
        if name == "crop":
            x, y, w, h = (int(v) for v in value)
            steps.append(f"(gimp-image-crop image {w} {h} {x} {y})")
        elif name == "resize":
            if isinstance(value, str) and value.endswith("%"):
                factor = float(value[:-1]) / 100
                steps.append("(gimp-image-scale image "
                             f"(round (* {factor} (car (gimp-image-width image)))) "
                             f"(round (* {factor} (car (gimp-image-height image)))))")
            else:
                steps.append(f"(gimp-image-scale image {int(value[0])} {int(value[1])})")
        elif name == "rotate":
            degrees = int(value) % 360
            if degrees not in _ROTATIONS:
                raise ImageToolError("GIMPAdapter rotates by 90, 180 or 270 degrees only")
            steps.append(f"(gimp-image-rotate image {_ROTATIONS[degrees]})")
        elif name == "flip":
            orientation = ("ORIENTATION-HORIZONTAL" if value == "horizontal"
                           else "ORIENTATION-VERTICAL")
            steps.append(f"(gimp-image-flip image {orientation})")
        elif name == "grayscale" and value:
            steps.append("(gimp-image-convert-grayscale image)")
        elif name == "blur":
            radius = float(value)
            steps.append("(plug-in-gauss RUN-NONINTERACTIVE image "
                         f"(car (gimp-image-get-active-drawable image)) {radius} {radius} 0)")
    src, dst = scheme_string(input_path), scheme_string(target)
    return (f"(let* ((image (car (gimp-file-load RUN-NONINTERACTIVE {src} {src}))))\n  "
            + "\n  ".join(steps) +
            "\n  (let ((drawable (car (gimp-image-flatten image))))\n"
            f"    (gimp-file-save RUN-NONINTERACTIVE image drawable {dst} {dst}))\n"
            "  (gimp-image-delete image))")


class GIMPAdapter(CLIToolMixin, ImageToolAdapter):
    """Image processing through GIMP's batch mode."""

    TOOLS = ["gimp-console", "gimp-console-2.10", "gimp"]
    HINT = "install GIMP 2.10"
    DEFAULT_TIMEOUT = 300.0
    ERROR = ImageToolError

    def __init__(self):
        self.connected = False
        self.last_script = ""

    def connect(self, config: Dict[str, Any]) -> None:
        """Locate gimp (or gimp-console)."""
        self._configure_cli(config)
        self.connected = True

    def process(self, input_path: str, operations: Dict[str, Any]) -> str:
        """Run the Script-Fu program; return the output path."""
        if not self.connected:
            raise ImageToolError("GIMPAdapter is not connected")
        require_input(input_path)
        check_operations(operations, SUPPORTED)
        target, _ = output_path(input_path, operations)
        self.last_script = script_fu(input_path, target, operations)
        command = [self.executable, "-i", "-b", self.last_script, "-b", "(gimp-quit 0)"]
        self._run_cli(command)
        return target

    def disconnect(self) -> None:
        """Nothing to release."""
        self.connected = False
