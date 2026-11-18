# LLM Support

LLM API adapters for AI Platform. Every adapter sends real requests; none
returns a fabricated answer. An adapter that cannot reach its server, or
lacks a key, raises an `LLMError` subclass (`llm_exception.py`).

## Adapters

| Adapter | Protocol | Default endpoint | Key variable |
|---|---|---|---|
| `OpenAICompatibleAdapter` | OpenAI Chat Completions | none (set `base_url`) | optional `api_key_env` |
| `LocalAIAdapter` | OpenAI-compatible | `http://127.0.0.1:8080` | none |
| `OllamaAdapter` | OpenAI-compatible `/v1` + native `/api/chat` | `http://127.0.0.1:11434` | none |
| `PhiAdapter` | OpenAI-compatible | none (local or Azure AI) | optional |
| `OpenAIAdapter` | OpenAI-compatible | `https://api.openai.com` | `OPENAI_API_KEY` |
| `AzureOpenAIAdapter` | Azure deployments | none (resource URL) | `AZURE_OPENAI_API_KEY` |
| `DeepSeekAdapter` | OpenAI-compatible | `https://api.deepseek.com` | `DEEPSEEK_API_KEY` |
| `GrokAdapter` | OpenAI-compatible | `https://api.x.ai` | `XAI_API_KEY` |
| `MistralAdapter` | OpenAI-compatible | `https://api.mistral.ai` | `MISTRAL_API_KEY` |
| `TogetherAdapter` | OpenAI-compatible | `https://api.together.xyz` | `TOGETHER_API_KEY` |
| `QwenAdapter` | DashScope compatible mode | `https://dashscope-intl.aliyuncs.com/compatible-mode` | `DASHSCOPE_API_KEY` |
| `HuggingFaceAdapter` | Inference Providers router | `https://router.huggingface.co` | `HF_TOKEN` |
| `GoogleAdapter` | Gemini OpenAI-compatible | `https://generativelanguage.googleapis.com/v1beta/openai` | `GEMINI_API_KEY` |
| `AnthropicAdapter` | Messages API | `https://api.anthropic.com` | `ANTHROPIC_API_KEY` |
| `CohereAdapter` | Chat v2 | `https://api.cohere.com` | `CO_API_KEY` |
| `ReplicateAdapter` | Predictions | `https://api.replicate.com` | `REPLICATE_API_TOKEN` |
| `BedrockAdapter` | Converse (boto3) | AWS region | AWS credential chain |

Hosted adapters have no default `model`: provider model names change faster
than this code.

Verification status: local adapters (LocalAI, Ollama) are tested live in
`test/functional/integration_test/test_llm_local_live.py`; hosted adapters
are tested against a fake server / fake client only
(`test/basic-structural/static/basic_unit_test/common/test_llm_hosted_adapters.py`).

## Usage

```python
from ai_platform.common.llm.localai_adapter import LocalAIAdapter

llm = LocalAIAdapter()
llm.initialize({"base_url": "http://127.0.0.1:8081",
                "model": "bielik-15b-localai",
                "temperature": 0, "max_tokens": 256})

print(llm.generate("Ile wynosi 17 razy 23?"))          # text only

result = llm.chat_completion([{"role": "user", "content": "..."}])
print(result.text, result.finish_reason, result.truncated, result.usage)
llm.shutdown()
```
