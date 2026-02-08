"""Example usage of all framework adapters."""

from code.common.framework.framework_registry import get_registry
from code.common.framework.langchain_adapter import LangChainAdapter
from code.common.framework.langgraph_adapter import LangGraphAdapter
from code.common.framework.crewai_adapter import CrewAIAdapter
from code.common.framework.akka_adapter import AkkaAdapter
from code.common.framework.autogen_adapter import AutoGenAdapter
from code.common.framework.autogpt_adapter import AutoGPTAdapter
from code.common.framework.haystack_adapter import HaystackAdapter
from code.common.framework.griptape_adapter import GriptapeAdapter
from code.common.framework.langroid_adapter import LangroidAdapter
from code.common.framework.gradientj_adapter import GradientJAdapter
from code.common.framework.outlines_adapter import OutlinesAdapter
from code.common.framework.langdock_adapter import LangDockAdapter
from code.common.framework.semantic_kernel_adapter import SemanticKernelAdapter

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
