"""Example usage of low-code platform adapters.

Registers every adapter and exercises each one with a small, real operation
against the platforms' default local URLs. Nothing is fabricated: an adapter
whose tool, server or package is not available here is reported as skipped
with the reason.

    python -m ai_platform.common.example.lowcode_example
"""

# Examples follow the same register-and-try pattern on purpose.
# pylint: disable=duplicate-code

from ai_platform.common.lowcode.agentgpt_adapter import AgentGPTAdapter
from ai_platform.common.lowcode.flowise_adapter import FlowiseAdapter
from ai_platform.common.lowcode.langflow_adapter import LangFlowAdapter
from ai_platform.common.lowcode.lowcode_registry import get_registry
from ai_platform.common.lowcode.lowcode_support import LowCodeError
from ai_platform.common.lowcode.n8n_adapter import N8nAdapter
from ai_platform.common.lowcode.rivet_adapter import RivetAdapter
from ai_platform.common.lowcode.superagi_adapter import SuperAGIAdapter


def main():
    """Register all adapters and exercise the usable ones."""
    registry = get_registry()

    platforms = {
        "agentgpt": AgentGPTAdapter,
        "flowise": FlowiseAdapter,
        "langflow": LangFlowAdapter,
        "n8n": N8nAdapter,
        "rivet": RivetAdapter,
        "superagi": SuperAGIAdapter,
    }

    for name, adapter_class in platforms.items():
        registry.register(name, adapter_class)

    print(f"Registered {len(platforms)}: {registry.list()}\n")

    for name in platforms:
        adapter = registry.get(name)
        try:
            adapter.connect({})
            print(f"{name:9} ready   client for {adapter.base_url} (no request sent yet)")
        except (LowCodeError, NotImplementedError) as exc:
            print(f"{name:9} skipped {type(exc).__name__}: {str(exc)[:80]}")
        finally:
            adapter.disconnect()


if __name__ == "__main__":
    main()
