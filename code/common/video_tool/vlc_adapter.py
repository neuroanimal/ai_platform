"""VLC adapter (headless ``cvlc`` transcoding through the stream output chain).

Builds a ``--sout`` chain and runs VLC without an interface::

    cvlc -q in.mp4 --start-time=5 --stop-time=15 \\
         --sout "#transcode{vcodec=h264,acodec=mp4a,width=640,fps=25}\\
                 :std{access=file,mux=mp4,dst=out.mp4}" \\
         vlc://quit

Operations: ``trim``, ``scale`` (width/height; 0 or negative = keep aspect),
``fps``, ``mute``, ``extract_audio``, ``video_codec`` / ``audio_codec``
(VLC FourCCs such as h264, mp4a, mp3, vorb), ``format`` / ``output``.

Not verified against an installed VLC here; unit tests check the generated
command. Configuration: ``timeout`` (default 3600), ``executable``,
``runner`` (tests). Previously a stub that returned a fake path; the class
name and the VideoToolAdapter methods are unchanged.
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

SUPPORTED = ("trim", "scale", "fps", "mute", "extract_audio", "video_codec", "audio_codec")
_MUX = {"mp4": "mp4", "m4a": "mp4", "mkv": "mkv", "webm": "webm", "ogg": "ogg", "ogv": "ogg",
        "ts": "ts", "mp3": "raw", "wav": "wav", "avi": "avi"}


def sout_chain(target: str, ext: str, operations: Dict[str, Any]) -> str:
    """VLC stream-output chain for the operations."""
    if ext not in _MUX:
        raise VideoToolError(f"VLCAdapter writes {sorted(_MUX)}, not {ext!r}")
    options: List[str] = []
    if operations.get("extract_audio"):
        options.append("vcodec=none")
        options.append(f"acodec={operations.get('audio_codec', 'mp4a')}")
    else:
        options.append(f"vcodec={operations.get('video_codec', 'h264')}")
        if operations.get("mute"):
            options.append("acodec=none")
        else:
            options.append(f"acodec={operations.get('audio_codec', 'mp4a')}")
        if "scale" in operations:
            width, height = (int(v) for v in operations["scale"])
            if width > 0:
                options.append(f"width={width}")
            if height > 0:
                options.append(f"height={height}")
        if "fps" in operations:
            options.append(f"fps={float(operations['fps']):g}")
    # The destination is quoted inside the chain; quotes in the path are rejected.
    if "'" in target or '"' in target:
        raise VideoToolError("output path must not contain quotes")
    return (f"#transcode{{{','.join(options)}}}"
            f":std{{access=file,mux={_MUX[ext]},dst='{target}'}}")


class VLCAdapter(CLIToolMixin, VideoToolAdapter):
    """Video transcoding through headless VLC."""

    TOOLS = ["cvlc", "vlc"]
    HINT = "install VLC"
    DEFAULT_TIMEOUT = 3600.0
    ERROR = VideoToolError

    def __init__(self):
        self.connected = False

    def connect(self, config: Dict[str, Any]) -> None:
        """Locate cvlc (or vlc)."""
        self._configure_cli(config)
        self.connected = True

    def process(self, input_path: str, operations: Dict[str, Any]) -> str:
        """Run VLC once; return the output path."""
        if not self.connected:
            raise VideoToolError("VLCAdapter is not connected")
        require_input(input_path)
        check_operations(operations, SUPPORTED)
        target, ext = output_path(input_path, operations)
        command = [self.executable, "-q", "-I", "dummy", input_path]
        if "trim" in operations:
            start, duration = (float(v) for v in operations["trim"])
            command += [f"--start-time={start:g}", f"--stop-time={start + duration:g}"]
        command += ["--sout", sout_chain(target, ext, operations), "vlc://quit"]
        self._run_cli(command)
        return target

    def disconnect(self) -> None:
        """Nothing to release."""
        self.connected = False
