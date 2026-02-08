"""Example usage of image tool adapters."""

from code.common.image_tool.image_tool_registry import get_registry
from code.common.image_tool.gimp_adapter import GIMPAdapter
from code.common.image_tool.dia_adapter import DiaAdapter
from code.common.image_tool.imagemagick_adapter import ImageMagickAdapter
from code.common.image_tool.inkscape_tool_adapter import InkscapeToolAdapter

def main():
    registry = get_registry()

    tools = {
        "gimp": GIMPAdapter,
        "dia": DiaAdapter,
        "imagemagick": ImageMagickAdapter,
        "inkscape": InkscapeToolAdapter,
    }

    for name, adapter_class in tools.items():
        registry.register(name, adapter_class)

    print(f"Registered {len(tools)} image tools: {registry.list()}\n")

    for name in tools.keys():
        adapter = registry.get(name)
        adapter.connect({})
        result = adapter.process("input.png", {"resize": "800x600"})
        print(f"{name}: {result}")
        adapter.disconnect()

if __name__ == "__main__":
    main()
