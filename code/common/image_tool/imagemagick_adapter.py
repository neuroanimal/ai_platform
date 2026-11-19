"""ImageMagick adapter (command line, ImageMagick 7 ``magick`` or 6 ``convert``).

Translates the operation model of ``image_operations.py`` into one
ImageMagick command, in operation order, and runs it for real::

    magick in.png -crop 100x50+10+20 +repage -resize 50% -rotate 90 out.jpg

Configuration: ``timeout`` (default 120), ``executable``, ``runner`` (tests).
Previously a stub that returned a fake path and processed nothing; the
class name and the ImageToolAdapter methods are unchanged.
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

SUPPORTED = ("crop", "resize", "rotate", "flip", "grayscale", "blur", "quality")


def imagemagick_arguments(operations: Dict[str, Any]) -> List[str]:
    """ImageMagick options for the operations, in order."""
    args: List[str] = []
    for name, value in operations.items():
        if name == "crop":
            x, y, w, h = (int(v) for v in value)
            args += ["-crop", f"{w}x{h}+{x}+{y}", "+repage"]
        elif name == "resize":
            size = value if isinstance(value, str) else f"{int(value[0])}x{int(value[1])}!"
            args += ["-resize", size]
        elif name == "rotate":
            args += ["-rotate", str(float(value))]
        elif name == "flip":
            args.append("-flop" if value == "horizontal" else "-flip")
        elif name == "grayscale" and value:
            args += ["-colorspace", "Gray"]
        elif name == "blur":
            args += ["-blur", f"0x{float(value)}"]
        elif name == "quality":
            args += ["-quality", str(int(value))]
    return args


class ImageMagickAdapter(CLIToolMixin, ImageToolAdapter):
    """Image processing through the ImageMagick CLI."""

    TOOLS = ["magick", "convert"]
    HINT = "install ImageMagick"
    DEFAULT_TIMEOUT = 120.0
    ERROR = ImageToolError

    def __init__(self):
        self.connected = False

    def connect(self, config: Dict[str, Any]) -> None:
        """Locate magick (IM7) or convert (IM6)."""
        self._configure_cli(config)
        self.connected = True

    def process(self, input_path: str, operations: Dict[str, Any]) -> str:
        """Run one ImageMagick command; return the output path."""
        if not self.connected:
            raise ImageToolError("ImageMagickAdapter is not connected")
        require_input(input_path)
        check_operations(operations, SUPPORTED)
        target, _ = output_path(input_path, operations)
        command = [self.executable, input_path, *imagemagick_arguments(operations), target]
        self._run_cli(command)
        return target

    def disconnect(self) -> None:
        """Nothing to release."""
        self.connected = False
