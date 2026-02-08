# Low-Code/No-Code Platform Support

Adapters for visual workflow and agent builders.

## Supported Platforms

- **AgentGPT**: Autonomous AI agent platform
- **Flowise**: Drag-and-drop LLM flows
- **LangFlow**: Visual LangChain builder
- **n8n**: Workflow automation
- **Rivet**: Visual AI agent builder
- **SuperAGI**: Autonomous agent framework

## Usage

```python
from code.common.lowcode.lowcode_registry import get_registry
from code.common.lowcode.flowise_adapter import FlowiseAdapter

registry = get_registry()
registry.register("flowise", FlowiseAdapter)

platform = registry.get("flowise")
platform.connect({"api_url": "http://localhost:3000"})
workflow_id = platform.deploy_workflow({"name": "chatbot"})
result = platform.execute_workflow(workflow_id, {"input": "Hello"})
platform.disconnect()
```
