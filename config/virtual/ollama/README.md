# Ollama Modelfiles for the Bielik GGUF models (reference copies)

Live copies are in `~/models/ollama/`; the GGUF files in `~/models/gguf/` (from
Hugging Face `speakleash/*-GGUF`). Template: ChatML, the same as the template
embedded in the GGUF (`tokenizer.chat_template`).

| Ollama name | GGUF | note |
|---|---|---|
| `bielik-1.5b-v3:q4_k_m` | Bielik-1.5B-v3.0-Instruct-Q4_K_M | |
| `bielik-4.5b-v3:q8_0` | Bielik-4.5B-v3.0-Instruct.Q8_0 | **doubles letters when copying names** ("expresssion", "search_documments") - breaks tool calls |
| `bielik-4.5b-v3:fp16` | Bielik-4.5B-v3.0-Instruct-fp16 (9.5 GB) | copies names correctly; prefer it for tool use |
| `bielik-11b-v2.6:q4_k_m` | Bielik-11B-v2.6-Instruct.Q4_K_M | |

Finding (2026-11-19): the letter doubling is not the prompt template and not
`repeat_penalty` (1.0, 1.1 and default give the same output); the fp16 file of
the same model does not show it, so it comes with the published Q8_0 file.

Create: `ollama create <name> -f <Modelfile>`. If the snap CLI fails with
"cannot create transient scope", the HTTP API works: upload the GGUF with
`POST /api/blobs/sha256:<digest>` and `POST /api/create` with `files`,
`template` and `parameters`.
