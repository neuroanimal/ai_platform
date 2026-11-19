"""
Shared operation model of the video tool adapters.

``process(input_path, operations)`` returns the path of the written file::

    {"trim": [start_seconds, duration_seconds],
     "scale": [width, height],           # -1 / -2 keeps the aspect ratio (FFmpeg)
     "fps": 25,
     "mute": True,                       # drop the audio stream
     "extract_audio": True,              # audio only (output e.g. .mp3/.wav/.m4a)
     "video_codec": "libx264", "audio_codec": "aac", "crf": 23,
     "format": "mp4",                    # output extension (default: input's)
     "output": "/path/out.mp4"}          # default: <input>_processed.<ext>

Unsupported operations raise ``VideoToolError`` instead of being skipped.
"""

import os
from typing import Any, Dict, Iterable, Tuple


class VideoToolError(Exception):
    """Invalid operations, missing tool or failed processing."""


def check_operations(operations: Dict[str, Any], supported: Iterable[str]) -> Dict[str, Any]:
    """Reject operations the adapter cannot perform, and contradictions."""
    if not isinstance(operations, dict):
        raise VideoToolError("operations must be a dict")
    allowed = set(supported) | {"output", "format"}
    unknown = [op for op in operations if op not in allowed]
    if unknown:
        raise VideoToolError(f"unsupported operations {unknown}; supported: {sorted(allowed)}")
    if operations.get("mute") and operations.get("extract_audio"):
        raise VideoToolError("'mute' and 'extract_audio' contradict each other")
    return operations


def output_path(input_path: str, operations: Dict[str, Any]) -> Tuple[str, str]:
    """Return (output path, extension without dot)."""
    if operations.get("output"):
        path = str(operations["output"])
        return path, os.path.splitext(path)[1].lstrip(".").lower()
    stem, ext = os.path.splitext(input_path)
    default = "m4a" if operations.get("extract_audio") else ext.lstrip(".")
    ext = (operations.get("format") or default).lower()
    return f"{stem}_processed.{ext}", ext


def require_input(input_path: str) -> None:
    """The input file must exist."""
    if not os.path.isfile(input_path):
        raise VideoToolError(f"input file not found: {input_path}")
