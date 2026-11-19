"""FFmpeg adapter (command line).

Translates the operation model of ``video_operations.py`` into one FFmpeg
command and runs it for real::

    ffmpeg -hide_banner -loglevel error -y -ss 5 -i in.mp4 -t 10 \\
           -vf scale=640:-2,fps=25 -c:v libx264 -crf 23 -an out.mp4

Input seeking (``-ss`` before ``-i``) is used for ``trim``; it is fast and,
with re-encoding, frame-accurate in current FFmpeg releases.

Configuration: ``timeout`` (default 3600), ``executable``, ``runner`` (tests).
Previously a stub that returned a fake path and processed nothing; the
class name and the VideoToolAdapter methods are unchanged.
"""

# The CLI adapters share their connect/process skeleton by design.
# pylint: disable=duplicate-code

from typing import Any, Dict, List

from ai_platform.common.util.cli_runner import CLIToolMixin
from ai_platform.common.video_tool.base import VideoToolAdapter
from ai_platform.common.video_tool.video_operations import (
    VideoToolError,
    check_operations,
    output_path,
    require_input,
)

SUPPORTED = ("trim", "scale", "fps", "mute", "extract_audio", "video_codec", "audio_codec", "crf")


def ffmpeg_command(executable: str, input_path: str, target: str,
                   operations: Dict[str, Any]) -> List[str]:
    """Full FFmpeg argument list for the operations."""
    command = [executable, "-hide_banner", "-loglevel", "error", "-y"]
    if "trim" in operations:
        command += ["-ss", str(float(operations["trim"][0]))]
    command += ["-i", input_path]
    if "trim" in operations:
        command += ["-t", str(float(operations["trim"][1]))]

    filters = []
    if "scale" in operations:
        width, height = operations["scale"]
        filters.append(f"scale={int(width)}:{int(height)}")
    if "fps" in operations:
        filters.append(f"fps={float(operations['fps']):g}")

    if operations.get("extract_audio"):
        if filters:
            raise VideoToolError("scale/fps cannot apply to an audio-only output")
        command.append("-vn")
    else:
        if filters:
            command += ["-vf", ",".join(filters)]
        if "video_codec" in operations:
            command += ["-c:v", str(operations["video_codec"])]
        if "crf" in operations:
            command += ["-crf", str(int(operations["crf"]))]
    if operations.get("mute"):
        command.append("-an")
    elif "audio_codec" in operations:
        command += ["-c:a", str(operations["audio_codec"])]
    command.append(target)
    return command


class FFmpegAdapter(CLIToolMixin, VideoToolAdapter):
    """Video processing through the FFmpeg CLI."""

    TOOLS = ["ffmpeg"]
    HINT = "install FFmpeg"
    DEFAULT_TIMEOUT = 3600.0
    ERROR = VideoToolError

    def __init__(self):
        self.connected = False

    def connect(self, config: Dict[str, Any]) -> None:
        """Locate ffmpeg."""
        self._configure_cli(config)
        self.connected = True

    def process(self, input_path: str, operations: Dict[str, Any]) -> str:
        """Run one FFmpeg command; return the output path."""
        if not self.connected:
            raise VideoToolError("FFmpegAdapter is not connected")
        require_input(input_path)
        check_operations(operations, SUPPORTED)
        target, _ = output_path(input_path, operations)
        self._run_cli(ffmpeg_command(self.executable, input_path, target, operations))
        return target

    def disconnect(self) -> None:
        """Nothing to release."""
        self.connected = False
