# LLM Support

LLM API adapters for AI Platform.

## Supported LLMs

- **OpenAI**: GPT-4, GPT-3.5
- **Anthropic**: Claude 3 (Opus, Sonnet, Haiku)
- **Google**: Gemini Pro
- **Cohere**: Command
- **Mistral**: Mistral Large
- **HuggingFace**: Open models
- **AWS Bedrock**: Titan, Claude
- **Azure OpenAI**: GPT-4
- **Ollama**: Local models
- **Together AI**: Open models
- **Replicate**: Cloud models

## Usage

```python
from code.common.llm.llm_registry import get_registry
from code.common.llm.openai_adapter import OpenAIAdapter

registry = get_registry()
registry.register("openai", OpenAIAdapter)

llm = registry.get("openai")
llm.initialize({"model": "gpt-4", "api_key": "..."})
response = llm.generate("Explain AI")
llm.shutdown()
```
