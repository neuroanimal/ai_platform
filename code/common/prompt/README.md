# Prompt Engineering Support

Prompt templating and management tool adapters.

## Supported Tools

- **Priompt**: JSX-based prompt engineering
- **PromptLayer**: Prompt management and versioning
- **LangChain PromptTemplate**: LangChain prompt templates
- **Guidance**: Microsoft's prompt library
- **LMQL**: Query language for LLMs

## Usage

```python
from code.common.prompt.prompt_registry import get_registry
from code.common.prompt.priompt_adapter import PriomptAdapter

registry = get_registry()
registry.register("priompt", PriomptAdapter)

prompt = registry.get("priompt")
prompt.initialize({})
result = prompt.render("Hello {name}", {"name": "World"})
print(result)
prompt.shutdown()
```
