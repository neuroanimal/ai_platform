"""Example usage of prompt adapters.

Registers every adapter and exercises each one with a small, real
operation. Nothing is fabricated: an adapter whose tool, server or
package is not available here is reported as skipped with the reason.

    python -m ai_platform.common.example.prompt_example
"""

# Examples follow the same register-and-try pattern on purpose.
# pylint: disable=duplicate-code

from ai_platform.common.prompt.guidance_adapter import GuidanceAdapter
from ai_platform.common.prompt.jinja2_prompt_adapter import Jinja2PromptAdapter, PromptError
from ai_platform.common.prompt.langchain_prompt_adapter import LangChainPromptAdapter
from ai_platform.common.prompt.lmql_adapter import LMQLAdapter
from ai_platform.common.prompt.priompt_adapter import PriomptAdapter
from ai_platform.common.prompt.prompt_registry import get_registry
from ai_platform.common.prompt.promptlayer_adapter import PromptLayerAdapter


def main():
    """Register all adapters and exercise the usable ones."""
    registry = get_registry()

    tools = {
        "jinja2": Jinja2PromptAdapter,
        "priompt": PriomptAdapter,
        "promptlayer": PromptLayerAdapter,
        "langchain_prompt": LangChainPromptAdapter,
        "guidance": GuidanceAdapter,
        "lmql": LMQLAdapter,
    }

    for name, adapter_class in tools.items():
        registry.register(name, adapter_class)

    print(f"Registered {len(tools)}: {registry.list()}\n")

    templates = {"jinja2": "Hello {{ name }}", "langchain_prompt": "Hello {name}",
                 "priompt": "Hello {name}", "promptlayer": "hello-template"}
    for name in tools:
        adapter = registry.get(name)
        try:
            adapter.initialize({})
            result = adapter.render(templates.get(name, "Hello {name}"), {"name": "World"})
            print(f"{name:17} OK      {result!r}")
        except (PromptError, NotImplementedError) as exc:
            print(f"{name:17} skipped {type(exc).__name__}: {str(exc)[:80]}")
        finally:
            adapter.shutdown()


if __name__ == "__main__":
    main()
