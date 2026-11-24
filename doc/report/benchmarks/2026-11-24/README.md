# Benchmark of 2026-11-24: agent with RAG (local models on Ollama, CPU)

| report | what | open |
|---|---|---|
| `agent_rag_ollama_20261124_rescreened` | 4 models x 3 variants (plain RAG, agent with search, agent with search + calculator), `agent_rag` (11 tasks about the fictional firm Nordwind, PL/EN), embedder bge-m3, top-k 3 | `.html` |

Re-screened once, without new model calls, after declined Polish forms
(Halinę Wrzos, Warszawę) were added to the accepted answers. "Right" is the
rule-based screening; manual_review rows were read by hand: almost all are
refusals ("no information") or answers without the requested calculation.

## Second run (same day): RAG prompt v2, score floor 0.6, search-first agent

| report | what |
|---|---|
| `agent_rag_v2_ollama_20261124` | qwen2.5:3b, llama3.2:3b, gemma3:4b, gemma3:1b x 4 variants (adds `search_first_calc`: passages preloaded, then search + calculator) |
| `agent_rag_v2_bielik45_20261124` | bielik-4.5b-v3:fp16, variants rag and search_first_calc |

Changes against the first run: the RAG system prompt says passages may be
off-topic and allows general knowledge (`RAG_SYSTEM`; the first is kept as
`RAG_SYSTEM_V1`), and passages scoring below 0.6 (bge-m3) are dropped. General
questions are now answered right by every model in plain RAG (llama3.2:3b
0/2 -> 2/2). The floor also drops one needed passage (founding year for
`calc_years_pl`, score 0.48), hence "Facts found" 8/9.
