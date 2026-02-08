"""Example usage of low-code/no-code platform adapters."""

from code.common.lowcode.lowcode_registry import get_registry
from code.common.lowcode.agentgpt_adapter import AgentGPTAdapter
from code.common.lowcode.flowise_adapter import FlowiseAdapter
from code.common.lowcode.langflow_adapter import LangFlowAdapter
from code.common.lowcode.n8n_adapter import N8nAdapter
from code.common.lowcode.rivet_adapter import RivetAdapter
from code.common.lowcode.superagi_adapter import SuperAGIAdapter

def main():
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

    print(f"Registered {len(platforms)} platforms: {registry.list()}\n")

    for name in platforms.keys():
        adapter = registry.get(name)
        adapter.connect({})
        workflow_id = adapter.deploy_workflow({"name": "test"})
        result = adapter.execute_workflow(workflow_id, {"input": "test"})
        print(f"{result['platform']}: {result['status']}")
        adapter.disconnect()

if __name__ == "__main__":
    main()
