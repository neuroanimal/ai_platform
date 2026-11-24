# Benchmark of 2026-11-24: agent with RAG (local models on Ollama, CPU)

| report | what | open |
|---|---|---|
| `agent_rag_ollama_20261124_rescreened` | 4 models x 3 variants (plain RAG, agent with search, agent with search + calculator), `agent_rag` (11 tasks about the fictional firm Nordwind, PL/EN), embedder bge-m3, top-k 3 | `.html` |

Re-screened once, without new model calls, after declined Polish forms
(Halinę Wrzos, Warszawę) were added to the accepted answers. "Right" is the
rule-based screening; manual_review rows were read by hand: almost all are
refusals ("no information") or answers without the requested calculation.
