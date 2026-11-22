# Benchmarks of 2026-11-19 (local models on Ollama / LocalAI, CPU)

Versioned results of the first benchmark day. `config/test_env/results/` is the
working directory (ignored by git); what is worth keeping is copied here.

| report | what | open |
|---|---|---|
| `llm_benchmark_ollama_v3_11models_20261119` | 11 models, `bilingual_reasoning@3` (16 tasks, PL/EN, 2 runs), max_tokens 768 | `.html` |
| `..._reviewed` + `..._screening_reviewed.json` | the same with 36 human verdicts (greg); rule/human agreement 28/28 | `.html` |
| `llm_benchmark_ollama_11models_20261119` | 11 models, `bilingual_reasoning@2` (4 tasks), max_tokens 384 | `.html` |
| `llm_benchmark_ollama_bielik11b_pl_maxtok1024_20261119` | Bielik 11B, Polish, max_tokens 1024 (supplement: 384 cut it off) | `.html` |
| `retrieval_bilingual_20261119` | embedders on the bilingual corpus (bge-m3 vs nomic vs lexical) | `.html` |
| `rag_qa_bilingual_20261119` | closed-book vs RAG question answering, 5 models | `.html` |
| `tool_use_ollama_20261119` | tool-using agent, 8 models, modes auto/json | `.html` |
| `tool_use_ollama_bielik45_fp16_20261119` | Bielik 4.5B fp16 (the Q8_0 GGUF doubles letters in names) | `.html` |

Kept: the raw report JSON of each final run (re-screening needs it), the human
review, and the rendered tables. Not kept (reproducible from what is here, or
superseded): the per-run parts that were merged into the 11-model reports, plain
screening files (`screen` recomputes them), review spreadsheets (the verdicts are
in `_screening_reviewed.json`), and the pre-integration `test_*.json` outputs.

Screening in these files is version 4.8; scores are rule-based pre-assessments
unless marked as human verdicts.
