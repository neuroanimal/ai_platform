# Retrieval: bilingual_retrieval@1, embedders compared (Ollama and LocalAI)

> 16 queries on 12 documents: a quick, reproducible comparison, not a benchmark of general retrieval quality. Most queries are cross-lingual on purpose.

Retrieval set bilingual_retrieval@1: 12 documents, 16 queries, top_k 5, run 2026-11-19T10:44:28.230627+00:00

## Embedders

| Embedder | Status | Hit@1 | Hit@3 | MRR | Recall@5 | Index s | s / query | Error |
|---|---|---|---|---|---|---|---|---|
| hashing | PASS | 0.25 | 0.438 | 0.349 | 0.5 | 0.002 | 0.0015 |  |
| ollama:nomic-embed-text | PASS | 0.25 | 0.438 | 0.348 | 0.562 | 1.012 | 0.0438 |  |
| ollama:bge-m3 | PASS | 0.938 | 1.0 | 0.969 | 1.0 | 3.572 | 0.0913 |  |
| localai:bge-m3-localai | PASS | 0.938 | 1.0 | 0.969 | 1.0 | 9.16 | 1.2237 |  |

## By query direction

| Embedder | Direction | Hit@1 | Hit@3 | MRR |
|---|---|---|---|---|
| hashing | en->en | 1.0 | 1.0 | 1.0 |
| hashing | en->pl | 0.0 | 0.0 | 0.042 |
| hashing | pl->en | 0.167 | 0.5 | 0.333 |
| hashing | pl->pl | 0.5 | 1.0 | 0.667 |
| ollama:nomic-embed-text | en->en | 1.0 | 1.0 | 1.0 |
| ollama:nomic-embed-text | en->pl | 0.167 | 0.5 | 0.372 |
| ollama:nomic-embed-text | pl->en | 0.0 | 0.0 | 0.0 |
| ollama:nomic-embed-text | pl->pl | 0.5 | 1.0 | 0.667 |
| ollama:bge-m3 | en->en | 1.0 | 1.0 | 1.0 |
| ollama:bge-m3 | en->pl | 1.0 | 1.0 | 1.0 |
| ollama:bge-m3 | pl->en | 0.833 | 1.0 | 0.917 |
| ollama:bge-m3 | pl->pl | 1.0 | 1.0 | 1.0 |
| localai:bge-m3-localai | en->en | 1.0 | 1.0 | 1.0 |
| localai:bge-m3-localai | en->pl | 1.0 | 1.0 | 1.0 |
| localai:bge-m3-localai | pl->en | 0.833 | 1.0 | 0.917 |
| localai:bge-m3-localai | pl->pl | 1.0 | 1.0 | 1.0 |

## Every query

| Embedder | Query | Direction | Text | Relevant | Retrieved (best first) | RR |
|---|---|---|---|---|---|---|
| hashing | q01 | pl->pl | Jak mierzy się wzrost cen w sklepach? | cpi_pl | cpi_pl, netconf_en, fx_en, rates_pl, cats_en | 1.0 |
| hashing | q02 | pl->en | Ile złotych trzeba zapłacić za dolara? | fx_en | cpi_pl, fx_en, rates_pl, cats_en, whales_en | 0.5 |
| hashing | q03 | pl->pl | Kto decyduje o wysokości oprocentowania kredytu? | rates_pl | cpi_pl, fx_en, rates_pl, cats_en, birds_pl | 0.333 |
| hashing | q04 | pl->en | Czy kot domowy jest ssakiem? | cats_en | canberra_pl, cpi_pl, fx_en, rates_pl, birds_pl | 0.0 |
| hashing | q05 | pl->en | Które zwierzę morskie karmi młode mlekiem? | whales_en | krakow_pl, yang_pl, birds_pl, netconf_en, fx_en | 0.0 |
| hashing | q06 | pl->en | Jakie miasto jest obecnie stolicą Polski? | warsaw_en | canberra_pl, krakow_pl, cats_en, whales_en, cpi_pl | 0.0 |
| hashing | q07 | pl->en | Jakim protokołem zmienia się konfigurację routera? | netconf_en | cpi_pl, netconf_en, fx_en, rates_pl, cats_en | 0.5 |
| hashing | q08 | pl->en | Czym są wykresy Helm w Kubernetesie? | helm_en | helm_en, cpi_pl, fx_en, rates_pl, cats_en | 1.0 |
| hashing | q09 | en->pl | Which city is the capital of Australia? | canberra_pl | warsaw_en, fx_en, netconf_en, yang_pl, helm_en | 0.0 |
| hashing | q10 | en->pl | Who sets the reference interest rate in Poland? | rates_pl | warsaw_en, fx_en, whales_en, netconf_en, helm_en | 0.0 |
| hashing | q11 | en->pl | Is a sparrow a bird? | birds_pl | netconf_en, canberra_pl, yang_pl, birds_pl, cpi_pl | 0.25 |
| hashing | q12 | en->pl | Where were Polish kings crowned? | krakow_pl | whales_en, fx_en, cpi_pl, rates_pl, cats_en | 0.0 |
| hashing | q13 | en->pl | What language describes configuration data models? | yang_pl | netconf_en, cpi_pl, fx_en, rates_pl, cats_en | 0.0 |
| hashing | q14 | en->pl | How is the change of consumer prices measured? | cpi_pl | fx_en, warsaw_en, netconf_en, yang_pl, helm_en | 0.0 |
| hashing | q15 | en->en | Do whales breathe air? | whales_en | whales_en, birds_pl, cpi_pl, fx_en, rates_pl | 1.0 |
| hashing | q16 | en->en | What tool packages applications for Kubernetes? | helm_en | helm_en, cats_en, netconf_en, cpi_pl, fx_en | 1.0 |
| ollama:nomic-embed-text | q01 | pl->pl | Jak mierzy się wzrost cen w sklepach? | cpi_pl | birds_pl, krakow_pl, cpi_pl, canberra_pl, rates_pl | 0.333 |
| ollama:nomic-embed-text | q02 | pl->en | Ile złotych trzeba zapłacić za dolara? | fx_en | birds_pl, krakow_pl, cpi_pl, yang_pl, rates_pl | 0.0 |
| ollama:nomic-embed-text | q03 | pl->pl | Kto decyduje o wysokości oprocentowania kredytu? | rates_pl | rates_pl, yang_pl, birds_pl, cpi_pl, krakow_pl | 1.0 |
| ollama:nomic-embed-text | q04 | pl->en | Czy kot domowy jest ssakiem? | cats_en | yang_pl, cpi_pl, birds_pl, krakow_pl, rates_pl | 0.0 |
| ollama:nomic-embed-text | q05 | pl->en | Które zwierzę morskie karmi młode mlekiem? | whales_en | birds_pl, yang_pl, krakow_pl, cpi_pl, rates_pl | 0.0 |
| ollama:nomic-embed-text | q06 | pl->en | Jakie miasto jest obecnie stolicą Polski? | warsaw_en | krakow_pl, rates_pl, birds_pl, canberra_pl, yang_pl | 0.0 |
| ollama:nomic-embed-text | q07 | pl->en | Jakim protokołem zmienia się konfigurację routera? | netconf_en | yang_pl, birds_pl, rates_pl, krakow_pl, cpi_pl | 0.0 |
| ollama:nomic-embed-text | q08 | pl->en | Czym są wykresy Helm w Kubernetesie? | helm_en | yang_pl, cpi_pl, krakow_pl, birds_pl, rates_pl | 0.0 |
| ollama:nomic-embed-text | q09 | en->pl | Which city is the capital of Australia? | canberra_pl | canberra_pl, warsaw_en, cats_en, fx_en, krakow_pl | 1.0 |
| ollama:nomic-embed-text | q10 | en->pl | Who sets the reference interest rate in Poland? | rates_pl | fx_en, warsaw_en, cpi_pl, yang_pl, rates_pl | 0.2 |
| ollama:nomic-embed-text | q11 | en->pl | Is a sparrow a bird? | birds_pl | cats_en, fx_en, whales_en, canberra_pl, krakow_pl | 0.0 |
| ollama:nomic-embed-text | q12 | en->pl | Where were Polish kings crowned? | krakow_pl | warsaw_en, krakow_pl, yang_pl, canberra_pl, cpi_pl | 0.5 |
| ollama:nomic-embed-text | q13 | en->pl | What language describes configuration data models? | yang_pl | netconf_en, helm_en, yang_pl, canberra_pl, fx_en | 0.333 |
| ollama:nomic-embed-text | q14 | en->pl | How is the change of consumer prices measured? | cpi_pl | fx_en, cats_en, netconf_en, helm_en, cpi_pl | 0.2 |
| ollama:nomic-embed-text | q15 | en->en | Do whales breathe air? | whales_en | whales_en, cats_en, canberra_pl, birds_pl, cpi_pl | 1.0 |
| ollama:nomic-embed-text | q16 | en->en | What tool packages applications for Kubernetes? | helm_en | helm_en, netconf_en, yang_pl, birds_pl, canberra_pl | 1.0 |
| ollama:bge-m3 | q01 | pl->pl | Jak mierzy się wzrost cen w sklepach? | cpi_pl | cpi_pl, rates_pl, fx_en, yang_pl, netconf_en | 1.0 |
| ollama:bge-m3 | q02 | pl->en | Ile złotych trzeba zapłacić za dolara? | fx_en | fx_en, rates_pl, cpi_pl, krakow_pl, canberra_pl | 1.0 |
| ollama:bge-m3 | q03 | pl->pl | Kto decyduje o wysokości oprocentowania kredytu? | rates_pl | rates_pl, fx_en, cpi_pl, netconf_en, helm_en | 1.0 |
| ollama:bge-m3 | q04 | pl->en | Czy kot domowy jest ssakiem? | cats_en | cats_en, birds_pl, whales_en, canberra_pl, krakow_pl | 1.0 |
| ollama:bge-m3 | q05 | pl->en | Które zwierzę morskie karmi młode mlekiem? | whales_en | whales_en, birds_pl, cats_en, canberra_pl, yang_pl | 1.0 |
| ollama:bge-m3 | q06 | pl->en | Jakie miasto jest obecnie stolicą Polski? | warsaw_en | krakow_pl, warsaw_en, canberra_pl, cats_en, fx_en | 0.5 |
| ollama:bge-m3 | q07 | pl->en | Jakim protokołem zmienia się konfigurację routera? | netconf_en | netconf_en, helm_en, yang_pl, rates_pl, fx_en | 1.0 |
| ollama:bge-m3 | q08 | pl->en | Czym są wykresy Helm w Kubernetesie? | helm_en | helm_en, yang_pl, netconf_en, cpi_pl, rates_pl | 1.0 |
| ollama:bge-m3 | q09 | en->pl | Which city is the capital of Australia? | canberra_pl | canberra_pl, warsaw_en, krakow_pl, whales_en, cats_en | 1.0 |
| ollama:bge-m3 | q10 | en->pl | Who sets the reference interest rate in Poland? | rates_pl | rates_pl, fx_en, warsaw_en, cpi_pl, netconf_en | 1.0 |
| ollama:bge-m3 | q11 | en->pl | Is a sparrow a bird? | birds_pl | birds_pl, whales_en, cats_en, canberra_pl, warsaw_en | 1.0 |
| ollama:bge-m3 | q12 | en->pl | Where were Polish kings crowned? | krakow_pl | krakow_pl, warsaw_en, fx_en, canberra_pl, birds_pl | 1.0 |
| ollama:bge-m3 | q13 | en->pl | What language describes configuration data models? | yang_pl | yang_pl, netconf_en, helm_en, cpi_pl, rates_pl | 1.0 |
| ollama:bge-m3 | q14 | en->pl | How is the change of consumer prices measured? | cpi_pl | cpi_pl, fx_en, rates_pl, netconf_en, yang_pl | 1.0 |
| ollama:bge-m3 | q15 | en->en | Do whales breathe air? | whales_en | whales_en, birds_pl, cats_en, warsaw_en, canberra_pl | 1.0 |
| ollama:bge-m3 | q16 | en->en | What tool packages applications for Kubernetes? | helm_en | helm_en, yang_pl, netconf_en, birds_pl, cpi_pl | 1.0 |
| localai:bge-m3-localai | q01 | pl->pl | Jak mierzy się wzrost cen w sklepach? | cpi_pl | cpi_pl, rates_pl, fx_en, yang_pl, netconf_en | 1.0 |
| localai:bge-m3-localai | q02 | pl->en | Ile złotych trzeba zapłacić za dolara? | fx_en | fx_en, rates_pl, cpi_pl, krakow_pl, canberra_pl | 1.0 |
| localai:bge-m3-localai | q03 | pl->pl | Kto decyduje o wysokości oprocentowania kredytu? | rates_pl | rates_pl, fx_en, cpi_pl, netconf_en, helm_en | 1.0 |
| localai:bge-m3-localai | q04 | pl->en | Czy kot domowy jest ssakiem? | cats_en | cats_en, birds_pl, whales_en, canberra_pl, krakow_pl | 1.0 |
| localai:bge-m3-localai | q05 | pl->en | Które zwierzę morskie karmi młode mlekiem? | whales_en | whales_en, birds_pl, cats_en, canberra_pl, yang_pl | 1.0 |
| localai:bge-m3-localai | q06 | pl->en | Jakie miasto jest obecnie stolicą Polski? | warsaw_en | krakow_pl, warsaw_en, canberra_pl, cats_en, fx_en | 0.5 |
| localai:bge-m3-localai | q07 | pl->en | Jakim protokołem zmienia się konfigurację routera? | netconf_en | netconf_en, helm_en, yang_pl, rates_pl, fx_en | 1.0 |
| localai:bge-m3-localai | q08 | pl->en | Czym są wykresy Helm w Kubernetesie? | helm_en | helm_en, yang_pl, netconf_en, cpi_pl, rates_pl | 1.0 |
| localai:bge-m3-localai | q09 | en->pl | Which city is the capital of Australia? | canberra_pl | canberra_pl, warsaw_en, krakow_pl, whales_en, cats_en | 1.0 |
| localai:bge-m3-localai | q10 | en->pl | Who sets the reference interest rate in Poland? | rates_pl | rates_pl, fx_en, warsaw_en, cpi_pl, netconf_en | 1.0 |
| localai:bge-m3-localai | q11 | en->pl | Is a sparrow a bird? | birds_pl | birds_pl, whales_en, cats_en, canberra_pl, warsaw_en | 1.0 |
| localai:bge-m3-localai | q12 | en->pl | Where were Polish kings crowned? | krakow_pl | krakow_pl, warsaw_en, fx_en, canberra_pl, birds_pl | 1.0 |
| localai:bge-m3-localai | q13 | en->pl | What language describes configuration data models? | yang_pl | yang_pl, netconf_en, helm_en, cpi_pl, rates_pl | 1.0 |
| localai:bge-m3-localai | q14 | en->pl | How is the change of consumer prices measured? | cpi_pl | cpi_pl, fx_en, rates_pl, netconf_en, yang_pl | 1.0 |
| localai:bge-m3-localai | q15 | en->en | Do whales breathe air? | whales_en | whales_en, birds_pl, cats_en, warsaw_en, canberra_pl | 1.0 |
| localai:bge-m3-localai | q16 | en->en | What tool packages applications for Kubernetes? | helm_en | helm_en, yang_pl, netconf_en, birds_pl, cpi_pl | 1.0 |
