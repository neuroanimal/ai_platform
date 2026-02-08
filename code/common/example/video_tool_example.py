"""Example usage of video tool adapters."""

from code.common.video_tool.video_tool_registry import get_registry
from code.common.video_tool.vlc_adapter import VLCAdapter
from code.common.video_tool.virtualdub_adapter import VirtualDubAdapter
from code.common.video_tool.ffmpeg_adapter import FFmpegAdapter

def main():
    registry = get_registry()

    tools = {
        "vlc": VLCAdapter,
        "virtualdub": VirtualDubAdapter,
        "ffmpeg": FFmpegAdapter,
    }

    for name, adapter_class in tools.items():
        registry.register(name, adapter_class)

    print(f"Registered {len(tools)} video tools: {registry.list()}\n")

    for name in tools.keys():
        adapter = registry.get(name)
        adapter.connect({})
        result = adapter.process("input.mp4", {"codec": "h264"})
        print(f"{name}: {result}")
        adapter.disconnect()

if __name__ == "__main__":
    main()
