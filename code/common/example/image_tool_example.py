"""Example usage of image tool adapters.

Registers every adapter and exercises each one with a small, real operation on
a generated PNG in a temporary directory. Nothing is fabricated: an adapter
whose tool, server or package is not available here is reported as skipped
with the reason.

    python -m ai_platform.common.example.image_tool_example
"""

# Examples follow the same register-and-try pattern on purpose.
# pylint: disable=duplicate-code

import os
import tempfile

from ai_platform.common.image_tool.dia_adapter import DiaAdapter
from ai_platform.common.image_tool.gimp_adapter import GIMPAdapter
from ai_platform.common.image_tool.image_operations import ImageToolError
from ai_platform.common.image_tool.image_tool_registry import get_registry
from ai_platform.common.image_tool.imagemagick_adapter import ImageMagickAdapter
from ai_platform.common.image_tool.inkscape_tool_adapter import InkscapeToolAdapter
from ai_platform.common.image_tool.pillow_image_adapter import PillowImageAdapter


def main():
    """Register all adapters and exercise the usable ones."""
    registry = get_registry()

    tools = {
        "pillow": PillowImageAdapter,
        "gimp": GIMPAdapter,
        "dia": DiaAdapter,
        "imagemagick": ImageMagickAdapter,
        "inkscape": InkscapeToolAdapter,
    }

    for name, adapter_class in tools.items():
        registry.register(name, adapter_class)

    print(f"Registered {len(tools)}: {registry.list()}\n")

    from PIL import Image  # pylint: disable=import-outside-toplevel
    with tempfile.TemporaryDirectory() as tmp:
        source = os.path.join(tmp, "in.png")
        Image.new("RGB", (64, 32), (200, 30, 30)).save(source)
        for name in tools:
            adapter = registry.get(name)
            try:
                adapter.connect({})
                out = adapter.process(source, {"resize": "50%"} if name != "inkscape"
                                      else {"width": 32})
                print(f"{name:11} OK      {os.path.basename(out)}")
            except ImageToolError as exc:
                print(f"{name:11} skipped {type(exc).__name__}: {str(exc)[:80]}")
            finally:
                adapter.disconnect()


if __name__ == "__main__":
    main()
