"""Pillow image adapter (new; add-only): in-process image processing.

Implements the whole operation model of ``image_operations.py`` with
Pillow, so image processing works without any external program. The CLI
adapters (ImageMagick, GIMP, Inkscape, Dia) cover what Pillow does not:
their own file formats and rendering engines.
"""

# The CLI adapters share their connect/process skeleton by design.
# pylint: disable=duplicate-code

from typing import Any, Dict

from ai_platform.common.image_tool.base import ImageToolAdapter
from ai_platform.common.image_tool.image_operations import (
    ImageToolError,
    check_operations,
    output_path,
    require_input,
)

SUPPORTED = ("crop", "resize", "rotate", "flip", "grayscale", "blur", "quality")
_SAVE_FORMAT = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "webp": "WEBP",
                "gif": "GIF", "bmp": "BMP", "tif": "TIFF", "tiff": "TIFF"}


class PillowImageAdapter(ImageToolAdapter):
    """Image processing with Pillow."""

    def __init__(self):
        self.connected = False
        self._image_module = None
        self._filter_module = None

    def connect(self, config: Dict[str, Any]) -> None:
        """Import Pillow."""
        try:
            from PIL import Image, ImageFilter  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise ImageToolError("PillowImageAdapter requires: pip install pillow") from exc
        self._image_module, self._filter_module = Image, ImageFilter
        self.connected = True

    def process(self, input_path: str, operations: Dict[str, Any]) -> str:
        """Apply operations in order and save; return the output path."""
        if not self.connected:
            raise ImageToolError("PillowImageAdapter is not connected")
        require_input(input_path)
        check_operations(operations, SUPPORTED)
        target, ext = output_path(input_path, operations)
        if ext not in _SAVE_FORMAT:
            raise ImageToolError(f"unsupported output format {ext!r}")

        image_mod = self._image_module
        with image_mod.open(input_path) as source:
            image = source.copy()
        for name, value in operations.items():
            if name == "crop":
                x, y, w, h = (int(v) for v in value)
                image = image.crop((x, y, x + w, y + h))
            elif name == "resize":
                image = image.resize(self._size(image, value), image_mod.Resampling.LANCZOS)
            elif name == "rotate":
                image = image.rotate(-float(value), expand=True)  # Pillow rotates counter-clockwise
            elif name == "flip":
                image = image.transpose(image_mod.Transpose.FLIP_LEFT_RIGHT if value == "horizontal"
                                        else image_mod.Transpose.FLIP_TOP_BOTTOM)
            elif name == "grayscale" and value:
                image = image.convert("L")
            elif name == "blur":
                image = image.filter(self._filter_module.GaussianBlur(float(value)))

        fmt = _SAVE_FORMAT[ext]
        if fmt == "JPEG" and image.mode not in ("RGB", "L"):
            image = image.convert("RGB")  # JPEG has no alpha channel
        options = {"quality": int(operations["quality"])} if "quality" in operations else {}
        image.save(target, fmt, **options)
        return target

    def disconnect(self) -> None:
        """Nothing to release."""
        self.connected = False

    @staticmethod
    def _size(image, value):
        if isinstance(value, str) and value.endswith("%"):
            factor = float(value[:-1]) / 100
            return max(1, round(image.width * factor)), max(1, round(image.height * factor))
        width, height = (int(v) for v in value)
        return width, height
