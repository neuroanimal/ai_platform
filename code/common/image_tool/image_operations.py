"""
Shared operation model of the image tool adapters.

``process(input_path, operations)`` takes an *ordered* dict of operations,
applied in insertion order, and returns the path of the written image::

    {"crop": [x, y, width, height],
     "resize": [width, height] | "50%",
     "rotate": degrees,                     # clockwise
     "flip": "horizontal" | "vertical",
     "grayscale": True,
     "blur": radius,
     "quality": 1..100,                     # JPEG/WebP output quality
     "format": "png" | "jpg" | ...,         # output format (default: input's)
     "output": "/path/out.png"}             # default: <input>_processed.<ext>

Each adapter declares which operations it supports; an unsupported one
raises ``ImageToolError`` instead of being skipped silently.
"""

import os
from typing import Any, Dict, Iterable, Tuple

KNOWN = ("crop", "resize", "rotate", "flip", "grayscale", "blur", "quality", "format",
         "output", "width", "height", "dpi", "area", "background")


class ImageToolError(Exception):
    """Invalid operations, missing tool or failed processing."""


def check_operations(operations: Dict[str, Any], supported: Iterable[str]) -> Dict[str, Any]:
    """Reject operations the adapter cannot perform."""
    if not isinstance(operations, dict):
        raise ImageToolError("operations must be a dict")
    allowed = set(supported) | {"output", "format"}
    unknown = [op for op in operations if op not in allowed]
    if unknown:
        raise ImageToolError(f"unsupported operations {unknown}; supported: {sorted(allowed)}")
    if "flip" in operations and operations["flip"] not in ("horizontal", "vertical"):
        raise ImageToolError("flip must be 'horizontal' or 'vertical'")
    return operations


def output_path(input_path: str, operations: Dict[str, Any],
                default_ext: str = "") -> Tuple[str, str]:
    """Return (output path, output extension without dot)."""
    if operations.get("output"):
        path = str(operations["output"])
        ext = operations.get("format") or os.path.splitext(path)[1].lstrip(".")
        return path, ext.lower()
    stem, ext = os.path.splitext(input_path)
    ext = (operations.get("format") or default_ext or ext.lstrip(".")).lower()
    return f"{stem}_processed.{ext}", ext


def require_input(input_path: str) -> None:
    """The input file must exist."""
    if not os.path.isfile(input_path):
        raise ImageToolError(f"input file not found: {input_path}")
