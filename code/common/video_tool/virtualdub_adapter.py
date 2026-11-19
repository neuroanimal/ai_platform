"""VirtualDub adapter - not implemented, on purpose.

VirtualDub (and VirtualDub2) is a Windows-only desktop application driven
by its own ``.vdscript`` language; it has no Linux build and no stable
headless interface that this platform (developed and tested on Linux/WSL2)
could run or verify.

Instead of returning a fake path (what the earlier stub did), every method
raises ``NotImplementedError``. ``FFmpegAdapter`` covers the same
processing (trim, scale, frame rate, codecs, audio) on every platform.

The class name is kept so that registries and imports do not break.
"""

from typing import Any, Dict

from ai_platform.common.video_tool.base import VideoToolAdapter

_MESSAGE = ("VirtualDubAdapter is not implemented: VirtualDub is Windows-only with no "
            "headless interface. Use FFmpegAdapter instead.")


class VirtualDubAdapter(VideoToolAdapter):
    """Placeholder that refuses to pretend; see the module docstring."""

    def connect(self, config: Dict[str, Any]) -> None:
        """Not implemented."""
        raise NotImplementedError(_MESSAGE)

    def process(self, input_path: str, operations: Dict[str, Any]) -> str:
        """Not implemented."""
        raise NotImplementedError(_MESSAGE)

    def disconnect(self) -> None:
        """Nothing to release."""
