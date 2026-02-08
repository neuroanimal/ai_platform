# Framework Support

AI/Agent framework adapters.

## Supported Frameworks

- **LangChain**: Chain-based LLM applications
- **LangGraph**: Graph-based agent workflows
- **CrewAI**: Multi-agent collaboration
- **Akka**: Actor-based distributed systems

## Usage

```python
from code.common.framework.framework_registry import get_registry
from code.common.framework.langchain_adapter import LangChainAdapter

registry = get_registry()
registry.register("langchain", LangChainAdapter)

adapter = registry.get("langchain")
adapter.initialize({"chain_type": "sequential"})
result = adapter.execute({"task": "summarize"})
adapter.shutdown()
```
