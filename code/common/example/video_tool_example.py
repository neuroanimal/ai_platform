"""Example usage of video tool adapters.

Registers every adapter and exercises each one with a small, real
operation. Nothing is fabricated: an adapter whose tool, server or
package is not available here is reported as skipped with the reason.

    python -m ai_platform.common.example.video_tool_example
"""

# Examples follow the same register-and-try pattern on purpose.
# pylint: disable=duplicate-code

from ai_platform.common.video_tool.ffmpeg_adapter import FFmpegAdapter
from ai_platform.common.video_tool.video_operations import VideoToolError
from ai_platform.common.video_tool.video_tool_registry import get_registry
from ai_platform.common.video_tool.virtualdub_adapter import VirtualDubAdapter
from ai_platform.common.video_tool.vlc_adapter import VLCAdapter


def main():
    """Register all adapters and exercise the usable ones."""
    registry = get_registry()

    tools = {
        "vlc": VLCAdapter,
        "virtualdub": VirtualDubAdapter,
        "ffmpeg": FFmpegAdapter,
    }

    for name, adapter_class in tools.items():
        registry.register(name, adapter_class)

    print(f"Registered {len(tools)}: {registry.list()}\n")

    for name in tools:
        adapter = registry.get(name)
        try:
            adapter.connect({})
            print(f"{name:10} OK      using {adapter.executable}")
        except (VideoToolError, NotImplementedError) as exc:
            print(f"{name:10} skipped {type(exc).__name__}: {str(exc)[:80]}")
        finally:
            adapter.disconnect()


if __name__ == "__main__":
    main()
