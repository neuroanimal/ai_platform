"""Example usage of all framework adapters."""

from ai_platform.common.framework.framework_registry import get_registry
from ai_platform.common.framework.langchain_adapter import LangChainAdapter
from ai_platform.common.framework.langgraph_adapter import LangGraphAdapter
from ai_platform.common.framework.crewai_adapter import CrewAIAdapter
from ai_platform.common.framework.akka_adapter import AkkaAdapter
from ai_platform.common.framework.autogen_adapter import AutoGenAdapter
from ai_platform.common.framework.autogpt_adapter import AutoGPTAdapter
from ai_platform.common.framework.haystack_adapter import HaystackAdapter
from ai_platform.common.framework.griptape_adapter import GriptapeAdapter
from ai_platform.common.framework.langroid_adapter import LangroidAdapter
from ai_platform.common.framework.gradientj_adapter import GradientJAdapter
from ai_platform.common.framework.outlines_adapter import OutlinesAdapter
from ai_platform.common.framework.langdock_adapter import LangDockAdapter
from ai_platform.common.framework.semantic_kernel_adapter import SemanticKernelAdapter

def main():
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

    print(f"Registered {len(frameworks)} frameworks: {registry.list()}\n")

    for name in frameworks.keys():
        adapter = registry.get(name)
        adapter.initialize({})
        result = adapter.execute({"task": "test"})
        print(f"{result['framework']}: OK")
        adapter.shutdown()

if __name__ == "__main__":
    main()
