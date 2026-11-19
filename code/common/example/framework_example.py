"""Example usage of agent framework adapters.

Registers every adapter and exercises each one with a small, real
operation - LangChain with the local LocalAI model when it
is running. Nothing is fabricated: an adapter whose tool, server or
package is not available here is reported as skipped with the reason.

    python -m ai_platform.common.example.framework_example
"""

# Examples follow the same register-and-try pattern on purpose.
# pylint: disable=duplicate-code

from ai_platform.common.framework.akka_adapter import AkkaAdapter
from ai_platform.common.framework.autogen_adapter import AutoGenAdapter
from ai_platform.common.framework.autogpt_adapter import AutoGPTAdapter
from ai_platform.common.framework.crewai_adapter import CrewAIAdapter
from ai_platform.common.framework.framework_registry import get_registry
from ai_platform.common.framework.framework_support import FrameworkError
from ai_platform.common.framework.gradientj_adapter import GradientJAdapter
from ai_platform.common.framework.griptape_adapter import GriptapeAdapter
from ai_platform.common.framework.haystack_adapter import HaystackAdapter
from ai_platform.common.framework.langchain_adapter import LangChainAdapter
from ai_platform.common.framework.langdock_adapter import LangDockAdapter
from ai_platform.common.framework.langgraph_adapter import LangGraphAdapter
from ai_platform.common.framework.langroid_adapter import LangroidAdapter
from ai_platform.common.framework.outlines_adapter import OutlinesAdapter
from ai_platform.common.framework.semantic_kernel_adapter import SemanticKernelAdapter
from ai_platform.common.llm.localai_adapter import LocalAIAdapter


def main():
    """Register all adapters and exercise the usable ones."""
    registry = get_registry()

    frameworks = {
        "langchain": LangChainAdapter,
        "langgraph": LangGraphAdapter,
        "crewai": CrewAIAdapter,
        "akka": AkkaAdapter,
        "autogen": AutoGenAdapter,
        "autogpt": AutoGPTAdapter,
        "haystack": HaystackAdapter,
        "griptape": GriptapeAdapter,
        "langroid": LangroidAdapter,
        "gradientj": GradientJAdapter,
        "outlines": OutlinesAdapter,
        "langdock": LangDockAdapter,
        "semantic_kernel": SemanticKernelAdapter,
    }

    for name, adapter_class in frameworks.items():
        registry.register(name, adapter_class)

    print(f"Registered {len(frameworks)}: {registry.list()}\n")

    llm = LocalAIAdapter()
    llm.initialize({"base_url": "http://127.0.0.1:8081", "model": "qwen25-05b-localai",
                    "max_tokens": 32, "temperature": 0})
    configs = {"langchain": {"prompt": "Answer in one word: {q}", "llm": llm},
               "langgraph": {"llm": llm},
               "akka": {"url": "http://127.0.0.1:9000"},
               "langdock": {"model": "gpt-4o"}}
    for name in frameworks:
        adapter = registry.get(name)
        try:
            adapter.initialize(configs.get(name, {}))
            task = {"input": "capital of Poland?", "path": "/status"}
            print(f"{name:16} OK      {str(adapter.execute(task)['output'])[:70]!r}")
        except (FrameworkError, NotImplementedError) as exc:
            print(f"{name:16} skipped {type(exc).__name__}: {str(exc)[:80]}")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            print(f"{name:16} skipped {type(exc).__name__}: {str(exc)[:80]}")
        finally:
            adapter.shutdown()


if __name__ == "__main__":
    main()
