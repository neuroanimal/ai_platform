# LocalAI model configurations (reference copies)

LocalAI reads model YAML files from its `--models-path`
(here `~/models/gguf/`), which lies outside the repository on purpose:
it also holds the multi-GB GGUF weights. The files in this directory are
the versioned reference copies; the live ones are copied from here.

| file | model | how the weights were obtained |
|---|---|---|
| `bge-m3-localai.yaml` | `bge-m3-localai` (embeddings, multilingual) | GGUF copied from Ollama's `bge-m3` blob into `~/models/gguf/bge-m3/bge-m3.gguf` |

Install / update:

```bash
cp config/virtual/localai/bge-m3-localai.yaml ~/models/gguf/
# LocalAI loads it on the first request to the model; no restart needed.
```

Start command used (2026-11-19):

```bash
local-ai run --address 127.0.0.1:8081 --models-path "$HOME/models/gguf" \
  --models-config-file "$HOME/models/gguf/localai-models-test29.yaml" \
  --backends-path "$HOME/models/localai/backends" \
  --data-path "$HOME/models/localai/state" --localai-config-dir "$HOME/models/localai/config" \
  --threads 8 --context-size 2048
```
