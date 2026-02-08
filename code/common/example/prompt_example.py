"""Example usage of prompt engineering adapters."""

from ai_platform.common.prompt.prompt_registry import get_registry
from ai_platform.common.prompt.priompt_adapter import PriomptAdapter
from ai_platform.common.prompt.promptlayer_adapter import PromptLayerAdapter
from ai_platform.common.prompt.langchain_prompt_adapter import LangChainPromptAdapter
from ai_platform.common.prompt.guidance_adapter import GuidanceAdapter
from ai_platform.common.prompt.lmql_adapter import LMQLAdapter

def main():
    registry = get_registry()

    tools = {
        "priompt": PriomptAdapter,
        "promptlayer": PromptLayerAdapter,
        "langchain_prompt": LangChainPromptAdapter,
        "guidance": GuidanceAdapter,
        "lmql": LMQLAdapter,
    }

    for name, adapter_class in tools.items():
        registry.register(name, adapter_class)

    print(f"Registered {len(tools)} prompt tools: {registry.list()}\n")

    for name in tools.keys():
        adapter = registry.get(name)
        adapter.initialize({})
        result = adapter.render("Hello {name}", {"name": "World"})
        print(f"{name}: {result}")
        adapter.shutdown()

if __name__ == "__main__":
    main()
