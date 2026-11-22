# RAG QA: closed-book vs RAG (bge-m3, top 3), bilingual_qa@1

> Screening is a rule-based pre-assessment, not a verdict. 'fictional' questions are about invented facts that only the corpus contains.

QA set bilingual_qa@1, embedder ollama:bge-m3, top_k 3, retrieval hit rate 1.00, run 2026-11-19T10:20:49.827915+00:00

## Summary

| Model | Mode | Questions | N | Correct | Incorrect | Manual review | Median s |
|---|---|---|---|---|---|---|---|
| bielik-1.5b-v3:q4_k_m | closed_book | all | 12 | 3 | 0 | 9 | 0.771 |
| bielik-1.5b-v3:q4_k_m | closed_book | fictional | 6 | 0 | 0 | 6 | 0.771 |
| bielik-1.5b-v3:q4_k_m | closed_book | general | 6 | 3 | 0 | 3 | 0.911 |
| bielik-1.5b-v3:q4_k_m | rag | all | 12 | 6 | 0 | 6 | 0.916 |
| bielik-1.5b-v3:q4_k_m | rag | fictional | 6 | 5 | 0 | 1 | 0.948 |
| bielik-1.5b-v3:q4_k_m | rag | general | 6 | 1 | 0 | 5 | 0.773 |
| bielik-4.5b-v3:q8_0 | closed_book | all | 12 | 4 | 1 | 7 | 2.64 |
| bielik-4.5b-v3:q8_0 | closed_book | fictional | 6 | 0 | 1 | 5 | 2.911 |
| bielik-4.5b-v3:q8_0 | closed_book | general | 6 | 4 | 0 | 2 | 1.761 |
| bielik-4.5b-v3:q8_0 | rag | all | 12 | 11 | 0 | 1 | 3.488 |
| bielik-4.5b-v3:q8_0 | rag | fictional | 6 | 6 | 0 | 0 | 5.076 |
| bielik-4.5b-v3:q8_0 | rag | general | 6 | 5 | 0 | 1 | 2.978 |
| gemma3:4b | closed_book | all | 12 | 5 | 0 | 7 | 0.753 |
| gemma3:4b | closed_book | fictional | 6 | 0 | 0 | 6 | 0.952 |
| gemma3:4b | closed_book | general | 6 | 5 | 0 | 1 | 0.638 |
| gemma3:4b | rag | all | 12 | 11 | 0 | 1 | 1.65 |
| gemma3:4b | rag | fictional | 6 | 6 | 0 | 0 | 1.888 |
| gemma3:4b | rag | general | 6 | 5 | 0 | 1 | 1.424 |
| llama3.2:3b | closed_book | all | 12 | 4 | 0 | 8 | 0.934 |
| llama3.2:3b | closed_book | fictional | 6 | 0 | 0 | 6 | 1.392 |
| llama3.2:3b | closed_book | general | 6 | 4 | 0 | 2 | 0.631 |
| llama3.2:3b | rag | all | 12 | 11 | 0 | 1 | 1.284 |
| llama3.2:3b | rag | fictional | 6 | 6 | 0 | 0 | 1.62 |
| llama3.2:3b | rag | general | 6 | 5 | 0 | 1 | 1.082 |
| qwen2.5:1.5b | closed_book | all | 12 | 4 | 0 | 8 | 0.746 |
| qwen2.5:1.5b | closed_book | fictional | 6 | 0 | 0 | 6 | 0.852 |
| qwen2.5:1.5b | closed_book | general | 6 | 4 | 0 | 2 | 0.68 |
| qwen2.5:1.5b | rag | all | 12 | 10 | 0 | 2 | 0.689 |
| qwen2.5:1.5b | rag | fictional | 6 | 6 | 0 | 0 | 1.197 |
| qwen2.5:1.5b | rag | general | 6 | 4 | 0 | 2 | 0.586 |

## Every answer

| Model | Mode | Item | Question | Expected | Retrieved | Screening | Answer |
|---|---|---|---|---|---|---|---|
| bielik-4.5b-v3:q8_0 | closed_book | f1 | Kto założył firmę Nordwind Logistyka? | Halina Wrzos\|Haliny Wrzos\|Halinę Wrzos\|Halinie Wrzos |  | manual_review | Firmę Nordwind Logistyka założył **Andrzej Kowalski**. |
| bielik-4.5b-v3:q8_0 | rag | f1 | Kto założył firmę Nordwind Logistyka? | Halina Wrzos\|Haliny Wrzos\|Halinę Wrzos\|Halinie Wrzos | nordwind_pl, fleet_en, code_pl | candidate_correct | Halina Wrzos. |
| bielik-4.5b-v3:q8_0 | closed_book | f2 | Kiedy zakończono projekt Orion w firmie Nordwind? | 14 marca 2025\|14 March 2025\|14.03.2025 |  | manual_review | Projekt Orion w firmie Nordwind został zakończony **w 2019 roku**. |
| bielik-4.5b-v3:q8_0 | rag | f2 | Kiedy zakończono projekt Orion w firmie Nordwind? | 14 marca 2025\|14 March 2025\|14.03.2025 | orion_en, nordwind_pl, fleet_en | candidate_correct | Projekt Orion w firmie Nordwind zakończono 14 marca 2025 roku. |
| bielik-4.5b-v3:q8_0 | closed_book | f3 | How much does the Nordwind Express subscription cost per month? | 49 |  | manual_review | The Nordwind Express subscription costs $19.99 per month. |
| bielik-4.5b-v3:q8_0 | rag | f3 | How much does the Nordwind Express subscription cost per month? | 49 | tariff_pl, support_en, fleet_en | candidate_correct_result_only | The Nordwinde Express subscription costs 49 zł per month. |
| bielik-4.5b-v3:q8_0 | closed_book | f4 | Ile ciężarówek elektrycznych ma Nordwind? | 19 |  | manual_review | Nordwind nie posiada informacji o liczbie ciężarówek elektrycznych. |
| bielik-4.5b-v3:q8_0 | rag | f4 | Ile ciężarówek elektrycznych ma Nordwind? | 19 | fleet_en, nordwind_pl, tariff_pl | candidate_correct_result_only | Nordwind ma 19 ciężarówek elektrycznych. |
| bielik-4.5b-v3:q8_0 | closed_book | f5 | What is the access code of Nordwind warehouse number 7? | 4512 |  | candidate_incorrect | The access code for Nordwind Warehouse number 7 is 12345. |
| bielik-4.5b-v3:q8_0 | rag | f5 | What is the access code of Nordwind warehouse number 7? | 4512 | code_pl, support_en, orion_en | candidate_correct_result_only | 4512 |
| bielik-4.5b-v3:q8_0 | closed_book | f6 | Do której godziny działa obsługa klienta Nordwind w dni robocze? | 16:45\|16.45 |  | manual_review | Obsługa klienta Nordwind w dni robocze działa do godziny **17:00**. |
| bielik-4.5b-v3:q8_0 | rag | f6 | Do której godziny działa obsługa klienta Nordwind w dni robocze? | 16:45\|16.45 | support_en, code_pl, fleet_en | candidate_correct | Obsługa klienta Nordwind działa w dni robocze od 7:15 do 16:45. |
| bielik-4.5b-v3:q8_0 | closed_book | g1 | Which city is the capital of Australia? | Canberra |  | candidate_correct | Australia's capital city is Canberra. |
| bielik-4.5b-v3:q8_0 | rag | g1 | Which city is the capital of Australia? | Canberra | canberra_pl, warsaw_en, krakow_pl | candidate_correct | Canberra |
| bielik-4.5b-v3:q8_0 | closed_book | g2 | Jakie miasto jest stolicą Polski? | Warszawa\|Warsaw\|Warszawie |  | candidate_correct | Warszawa. |
| bielik-4.5b-v3:q8_0 | rag | g2 | Jakie miasto jest stolicą Polski? | Warszawa\|Warsaw\|Warszawie | krakow_pl, warsaw_en, canberra_pl | manual_review | Kraków. |
| bielik-4.5b-v3:q8_0 | closed_book | g3 | Where were Polish kings crowned? | Wawel\|Kraków\|Krakow\|Cracow |  | candidate_correct | The Polish kings were crowned in Kraków, specifically at the Wawel Castle. |
| bielik-4.5b-v3:q8_0 | rag | g3 | Where were Polish kings crowned? | Wawel\|Kraków\|Krakow\|Cracow | krakow_pl, warsaw_en, fx_en | candidate_correct | Kraków. |
| bielik-4.5b-v3:q8_0 | closed_book | g4 | Jakim protokołem zmienia się konfigurację urządzeń sieciowych? | NETCONF |  | manual_review | HTTP (Hypertext Transfer Protocol). |
| bielik-4.5b-v3:q8_0 | rag | g4 | Jakim protokołem zmienia się konfigurację urządzeń sieciowych? | NETCONF | netconf_en, yang_pl, helm_en | candidate_correct | NETCONF. |
| bielik-4.5b-v3:q8_0 | closed_book | g5 | What do whales feed their young with? | milk\|mleko\|mlekiem |  | candidate_correct | Whales feed their young with milk. |
| bielik-4.5b-v3:q8_0 | rag | g5 | What do whales feed their young with? | milk\|mleko\|mlekiem | whales_en, birds_pl, cats_en | candidate_correct | Whales feed their young with milk. |
| bielik-4.5b-v3:q8_0 | closed_book | g6 | Jak nazywa się narzędzie pakujące aplikacje Kubernetes w wykresy? | Helm |  | manual_review | Kubechart. |
| bielik-4.5b-v3:q8_0 | rag | g6 | Jak nazywa się narzędzie pakujące aplikacje Kubernetes w wykresy? | Helm | helm_en, yang_pl, netconf_en | candidate_correct | Helm. |
| gemma3:4b | closed_book | f1 | Kto założył firmę Nordwind Logistyka? | Halina Wrzos\|Haliny Wrzos\|Halinę Wrzos\|Halinie Wrzos |  | manual_review | Władimir Żukov. |
| gemma3:4b | rag | f1 | Kto założył firmę Nordwind Logistyka? | Halina Wrzos\|Haliny Wrzos\|Halinę Wrzos\|Halinie Wrzos | nordwind_pl, fleet_en, code_pl | candidate_correct | Halina Wrzos. |
| gemma3:4b | closed_book | f2 | Kiedy zakończono projekt Orion w firmie Nordwind? | 14 marca 2025\|14 March 2025\|14.03.2025 |  | manual_review | Projekt Orion został zakończony w firmie Nordwind w 2023 roku. |
| gemma3:4b | rag | f2 | Kiedy zakończono projekt Orion w firmie Nordwind? | 14 marca 2025\|14 March 2025\|14.03.2025 | orion_en, nordwind_pl, fleet_en | candidate_correct | 14 marca 2025 roku. |
| gemma3:4b | closed_book | f3 | How much does the Nordwind Express subscription cost per month? | 49 |  | manual_review | €9.99 per month. |
| gemma3:4b | rag | f3 | How much does the Nordwind Express subscription cost per month? | 49 | tariff_pl, support_en, fleet_en | candidate_correct_result_only | 49 zł miesięcznie. |
| gemma3:4b | closed_book | f4 | Ile ciężarówek elektrycznych ma Nordwind? | 19 |  | manual_review | 3. |
| gemma3:4b | rag | f4 | Ile ciężarówek elektrycznych ma Nordwind? | 19 | fleet_en, nordwind_pl, tariff_pl | candidate_correct_result_only | 19 |
| gemma3:4b | closed_book | f5 | What is the access code of Nordwind warehouse number 7? | 4512 |  | manual_review | 789456 |
| gemma3:4b | rag | f5 | What is the access code of Nordwind warehouse number 7? | 4512 | code_pl, support_en, orion_en | candidate_correct_result_only | 4512 |
| gemma3:4b | closed_book | f6 | Do której godziny działa obsługa klienta Nordwind w dni robocze? | 16:45\|16.45 |  | manual_review | Do 18:00. |
| gemma3:4b | rag | f6 | Do której godziny działa obsługa klienta Nordwind w dni robocze? | 16:45\|16.45 | support_en, code_pl, fleet_en | candidate_correct | Do 16:45. |
| gemma3:4b | closed_book | g1 | Which city is the capital of Australia? | Canberra |  | candidate_correct | Canberra |
| gemma3:4b | rag | g1 | Which city is the capital of Australia? | Canberra | canberra_pl, warsaw_en, krakow_pl | candidate_correct | Canberra |
| gemma3:4b | closed_book | g2 | Jakie miasto jest stolicą Polski? | Warszawa\|Warsaw\|Warszawie |  | candidate_correct | Warszawa. |
| gemma3:4b | rag | g2 | Jakie miasto jest stolicą Polski? | Warszawa\|Warsaw\|Warszawie | krakow_pl, warsaw_en, canberra_pl | manual_review | Kraków. |
| gemma3:4b | closed_book | g3 | Where were Polish kings crowned? | Wawel\|Kraków\|Krakow\|Cracow |  | candidate_correct | Wawel Cathedral, Kraków |
| gemma3:4b | rag | g3 | Where were Polish kings crowned? | Wawel\|Kraków\|Krakow\|Cracow | krakow_pl, warsaw_en, fx_en | candidate_correct | On Wawel. |
| gemma3:4b | closed_book | g4 | Jakim protokołem zmienia się konfigurację urządzeń sieciowych? | NETCONF |  | manual_review | SNMP. |
| gemma3:4b | rag | g4 | Jakim protokołem zmienia się konfigurację urządzeń sieciowych? | NETCONF | netconf_en, yang_pl, helm_en | candidate_correct | NETCONF |
| gemma3:4b | closed_book | g5 | What do whales feed their young with? | milk\|mleko\|mlekiem |  | candidate_correct | Milk. |
| gemma3:4b | rag | g5 | What do whales feed their young with? | milk\|mleko\|mlekiem | whales_en, birds_pl, cats_en | candidate_correct | Milk. |
| gemma3:4b | closed_book | g6 | Jak nazywa się narzędzie pakujące aplikacje Kubernetes w wykresy? | Helm |  | candidate_correct | Helm |
| gemma3:4b | rag | g6 | Jak nazywa się narzędzie pakujące aplikacje Kubernetes w wykresy? | Helm | helm_en, yang_pl, netconf_en | candidate_correct | Helm packages Kubernetes applications as charts. |
| llama3.2:3b | closed_book | f1 | Kto założył firmę Nordwind Logistyka? | Halina Wrzos\|Haliny Wrzos\|Halinę Wrzos\|Halinie Wrzos |  | manual_review | Odpowiedź: Firma Nordwind Logistyka została założona przez Piotra Wachowskiego. |
| llama3.2:3b | rag | f1 | Kto założył firmę Nordwind Logistyka? | Halina Wrzos\|Haliny Wrzos\|Halinę Wrzos\|Halinie Wrzos | nordwind_pl, fleet_en, code_pl | candidate_correct | Halinę Wrzos. |
| llama3.2:3b | closed_book | f2 | Kiedy zakończono projekt Orion w firmie Nordwind? | 14 marca 2025\|14 March 2025\|14.03.2025 |  | manual_review | Odpowiedź: Projekt Orion w firmie Nordwind zakończono w 2011 roku. |
| llama3.2:3b | rag | f2 | Kiedy zakończono projekt Orion w firmie Nordwind? | 14 marca 2025\|14 March 2025\|14.03.2025 | orion_en, nordwind_pl, fleet_en | candidate_correct | Zakończono projekt Orion w firmie Nordwind 14 marca 2025 roku. |
| llama3.2:3b | closed_book | f3 | How much does the Nordwind Express subscription cost per month? | 49 |  | manual_review | I don't have the most current information on the Nordwind Express subscription cost. |
| llama3.2:3b | rag | f3 | How much does the Nordwind Express subscription cost per month? | 49 | tariff_pl, support_en, fleet_en | candidate_correct_result_only | 49 zł. |
| llama3.2:3b | closed_book | f4 | Ile ciężarówek elektrycznych ma Nordwind? | 19 |  | manual_review | Niestety nie mam informacji na temat liczby ciężarówek elektrycznych, które ma Nordwind. |
| llama3.2:3b | rag | f4 | Ile ciężarówek elektrycznych ma Nordwind? | 19 | fleet_en, nordwind_pl, tariff_pl | candidate_correct_result_only | Ile ciężarówek elektrycznych ma Nordwind to 19. |
| llama3.2:3b | closed_book | f5 | What is the access code of Nordwind warehouse number 7? | 4512 |  | manual_review | I don't have access to that information. |
| llama3.2:3b | rag | f5 | What is the access code of Nordwind warehouse number 7? | 4512 | code_pl, support_en, orion_en | candidate_correct_result_only | 4512 |
| llama3.2:3b | closed_book | f6 | Do której godziny działa obsługa klienta Nordwind w dni robocze? | 16:45\|16.45 |  | manual_review | Odpowiedź: W dni robocze od 9:00 do 18:00 (z wyjątkiem niedziel i świąt państwowych). |
| llama3.2:3b | rag | f6 | Do której godziny działa obsługa klienta Nordwind w dni robocze? | 16:45\|16.45 | support_en, code_pl, fleet_en | candidate_correct | Odpowiedź: Od 7:15 do 16:45. |
| llama3.2:3b | closed_book | g1 | Which city is the capital of Australia? | Canberra |  | candidate_correct | Canberra. |
| llama3.2:3b | rag | g1 | Which city is the capital of Australia? | Canberra | canberra_pl, warsaw_en, krakow_pl | candidate_correct | Canberra. |
| llama3.2:3b | closed_book | g2 | Jakie miasto jest stolicą Polski? | Warszawa\|Warsaw\|Warszawie |  | candidate_correct | Warszawa. |
| llama3.2:3b | rag | g2 | Jakie miasto jest stolicą Polski? | Warszawa\|Warsaw\|Warszawie | krakow_pl, warsaw_en, canberra_pl | candidate_correct | Według kontekstu, stolicą Polski jest Warszawa. |
| llama3.2:3b | closed_book | g3 | Where were Polish kings crowned? | Wawel\|Kraków\|Krakow\|Cracow |  | candidate_correct | In Wawel Cathedral in Kraków, Poland. |
| llama3.2:3b | rag | g3 | Where were Polish kings crowned? | Wawel\|Kraków\|Krakow\|Cracow | krakow_pl, warsaw_en, fx_en | manual_review | Wawelu. |
| llama3.2:3b | closed_book | g4 | Jakim protokołem zmienia się konfigurację urządzeń sieciowych? | NETCONF |  | manual_review | Protokołem zmiany konfiguracji urządzeń sieciowych jest Dynamic Host Configuration Protocol (DHCP). |
| llama3.2:3b | rag | g4 | Jakim protokołem zmienia się konfigurację urządzeń sieciowych? | NETCONF | netconf_en, yang_pl, helm_en | candidate_correct | NETCONF. |
| llama3.2:3b | closed_book | g5 | What do whales feed their young with? | milk\|mleko\|mlekiem |  | candidate_correct | Milk. |
| llama3.2:3b | rag | g5 | What do whales feed their young with? | milk\|mleko\|mlekiem | whales_en, birds_pl, cats_en | candidate_correct | Milk. |
| llama3.2:3b | closed_book | g6 | Jak nazywa się narzędzie pakujące aplikacje Kubernetes w wykresy? | Helm |  | manual_review | Odpowiedź: kubectl. |
| llama3.2:3b | rag | g6 | Jak nazywa się narzędzie pakujące aplikacje Kubernetes w wykresy? | Helm | helm_en, yang_pl, netconf_en | candidate_correct | Helm. |
| bielik-1.5b-v3:q4_k_m | closed_book | f1 | Kto założył firmę Nordwind Logistyka? | Halina Wrzos\|Haliny Wrzos\|Halinę Wrzos\|Halinie Wrzos |  | manual_review | Firma Nordwin Logistyka została założona przez dwóch braci: 1. **Andreasa Nordwina** - urodzonego 25 czerwca 1952 roku w miejscowości Schönfels w Niemczech. 2. **Jürgena Nordwina** - urodzonego 25 czerwca 1952 roku w tej samej miejscowości. Obaj bracia są założycielami firmy Nordwin Logistyka, która |
| bielik-1.5b-v3:q4_k_m | rag | f1 | Kto założył firmę Nordwind Logistyka? | Halina Wrzos\|Haliny Wrzos\|Halinę Wrzos\|Halinie Wrzos | nordwind_pl, fleet_en, code_pl | candidate_correct | Halina Wrzos. |
| bielik-1.5b-v3:q4_k_m | closed_book | f2 | Kiedy zakończono projekt Orion w firmie Nordwind? | 14 marca 2025\|14 March 2025\|14.03.2025 |  | manual_review | Projekt Orion w firmie Nordwind został zakończony w 2015 roku. |
| bielik-1.5b-v3:q4_k_m | rag | f2 | Kiedy zakończono projekt Orion w firmie Nordwind? | 14 marca 2025\|14 March 2025\|14.03.2025 | orion_en, nordwind_pl, fleet_en | candidate_correct | Projekt Orion w firmie Nordwind został ukończony 14 marca 2025 roku. |
| bielik-1.5b-v3:q4_k_m | closed_book | f3 | How much does the Nordwind Express subscription cost per month? | 49 |  | manual_review | The Nordwinde Express subscription costs $10 per month. |
| bielik-1.5b-v3:q4_k_m | rag | f3 | How much does the Nordwind Express subscription cost per month? | 49 | tariff_pl, support_en, fleet_en | candidate_correct_result_only | 49 zł. |
| bielik-1.5b-v3:q4_k_m | closed_book | f4 | Ile ciężarówek elektrycznych ma Nordwind? | 19 |  | manual_review | Nordwinnüd ma 10 ciężarówek elektrycznych. |
| bielik-1.5b-v3:q4_k_m | rag | f4 | Ile ciężarówek elektrycznych ma Nordwind? | 19 | fleet_en, nordwind_pl, tariff_pl | candidate_correct_result_only | Nordwind ma 19 ciężarówek elektrycznych. |
| bielik-1.5b-v3:q4_k_m | closed_book | f5 | What is the access code of Nordwind warehouse number 7? | 4512 |  | manual_review | The access code for the Nordwinn warehouse number 7 is "1234". |
| bielik-1.5b-v3:q4_k_m | rag | f5 | What is the access code of Nordwind warehouse number 7? | 4512 | code_pl, support_en, orion_en | manual_review | I do not know. |
| bielik-1.5b-v3:q4_k_m | closed_book | f6 | Do której godziny działa obsługa klienta Nordwind w dni robocze? | 16:45\|16.45 |  | manual_review | Obsługa klienta Nordwinda w dni robocze jest dostępna od poniedziałku do piątku w godzinach 10:00 - 18:00. |
| bielik-1.5b-v3:q4_k_m | rag | f6 | Do której godziny działa obsługa klienta Nordwind w dni robocze? | 16:45\|16.45 | support_en, code_pl, fleet_en | candidate_correct | Obsługa klienta Nordwindu działa od 7:15 do 16:45 w dni robocze. |
| bielik-1.5b-v3:q4_k_m | closed_book | g1 | Which city is the capital of Australia? | Canberra |  | candidate_correct | The capital city of Australia is Canberra. |
| bielik-1.5b-v3:q4_k_m | rag | g1 | Which city is the capital of Australia? | Canberra | canberra_pl, warsaw_en, krakow_pl | manual_review | I don't know. |
| bielik-1.5b-v3:q4_k_m | closed_book | g2 | Jakie miasto jest stolicą Polski? | Warszawa\|Warsaw\|Warszawie |  | candidate_correct | Warszawa. |
| bielik-1.5b-v3:q4_k_m | rag | g2 | Jakie miasto jest stolicą Polski? | Warszawa\|Warsaw\|Warszawie | krakow_pl, warsaw_en, canberra_pl | manual_review | Kraków. |
| bielik-1.5b-v3:q4_k_m | closed_book | g3 | Where were Polish kings crowned? | Wawel\|Kraków\|Krakow\|Cracow |  | candidate_correct | The Polish kings were crowned in the **Krakow** Cathedral. |
| bielik-1.5b-v3:q4_k_m | rag | g3 | Where were Polish kings crowned? | Wawel\|Kraków\|Krakow\|Cracow | krakow_pl, warsaw_en, fx_en | manual_review | I do not know. |
| bielik-1.5b-v3:q4_k_m | closed_book | g4 | Jakim protokołem zmienia się konfigurację urządzeń sieciowych? | NETCONF |  | manual_review | Protokołem używanym do zmiany konfiguracji urządzeń sieciowych jest **RFC 2199** (ang. **RFC 2199**). |
| bielik-1.5b-v3:q4_k_m | rag | g4 | Jakim protokołem zmienia się konfigurację urządzeń sieciowych? | NETCONF | netconf_en, yang_pl, helm_en | manual_review | ollama: HTTP 500 from http://127.0.0.1:11434/v1/chat/completions: {"error":{"message":"prediction aborted, token repeat limit reached","type":"api_error","param":null,"code":null}} |
| bielik-1.5b-v3:q4_k_m | closed_book | g5 | What do whales feed their young with? | milk\|mleko\|mlekiem |  | manual_review | Whales feed their young with a special type of blubber called "blubber cap" or "blubber ball". This is a large, fat-filled sac that is produced by the mother whale and is passed to her calf or calf-to-calf. The blubber cap is a rich source of nutrients, including fatty acids, proteins, and vitamins, |
| bielik-1.5b-v3:q4_k_m | rag | g5 | What do whales feed their young with? | milk\|mleko\|mlekiem | whales_en, birds_pl, cats_en | manual_review | I do not know. |
| bielik-1.5b-v3:q4_k_m | closed_book | g6 | Jak nazywa się narzędzie pakujące aplikacje Kubernetes w wykresy? | Helm |  | manual_review | Operator do pakowania aplikacji Kubernetes w wykresy nazywa się `kube-app-packer`. |
| bielik-1.5b-v3:q4_k_m | rag | g6 | Jak nazywa się narzędzie pakujące aplikacje Kubernetes w wykresy? | Helm | helm_en, yang_pl, netconf_en | candidate_correct | Helm. |
| qwen2.5:1.5b | closed_book | f1 | Kto założył firmę Nordwind Logistyka? | Halina Wrzos\|Haliny Wrzos\|Halinę Wrzos\|Halinie Wrzos |  | manual_review | Nordwind Logistyka nie jest firmą prawdziwą, ale jest to nazwa firmy, która jest często używana w reklamach i reklamowych materiałach. Jest to nieprawdopodobne, że ktoś założył tą firmę, ponieważ nie istnieje prawdziwa firma o takim nazwie. |
| qwen2.5:1.5b | rag | f1 | Kto założył firmę Nordwind Logistyka? | Halina Wrzos\|Haliny Wrzos\|Halinę Wrzos\|Halinie Wrzos | nordwind_pl, fleet_en, code_pl | candidate_correct | Halinę Wrzos |
| qwen2.5:1.5b | closed_book | f2 | Kiedy zakończono projekt Orion w firmie Nordwind? | 14 marca 2025\|14 March 2025\|14.03.2025 |  | manual_review | Projekt Orion w firmie Nordwind zakończył się w 2011 roku. |
| qwen2.5:1.5b | rag | f2 | Kiedy zakończono projekt Orion w firmie Nordwind? | 14 marca 2025\|14 March 2025\|14.03.2025 | orion_en, nordwind_pl, fleet_en | candidate_correct | Projekt Orion w firmie Nordwind zakończył się 14 marca 2025 roku. |
| qwen2.5:1.5b | closed_book | f3 | How much does the Nordwind Express subscription cost per month? | 49 |  | manual_review | The Nordwind Express subscription costs $19.99 per month. |
| qwen2.5:1.5b | rag | f3 | How much does the Nordwind Express subscription cost per month? | 49 | tariff_pl, support_en, fleet_en | candidate_correct_result_only | The Nordwind Express subscription costs 49 zł per month. |
| qwen2.5:1.5b | closed_book | f4 | Ile ciężarówek elektrycznych ma Nordwind? | 19 |  | manual_review | Nordwind ma 12 ciężarówek elektrycznych. |
| qwen2.5:1.5b | rag | f4 | Ile ciężarówek elektrycznych ma Nordwind? | 19 | fleet_en, nordwind_pl, tariff_pl | candidate_correct_result_only | Nordwind ma 19 ciężarówek elektrycznych. |
| qwen2.5:1.5b | closed_book | f5 | What is the access code of Nordwind warehouse number 7? | 4512 |  | manual_review | I'm sorry, but I don't have any information about Nordwind warehouse number 7 or its access code. I can't provide that specific answer. |
| qwen2.5:1.5b | rag | f5 | What is the access code of Nordwind warehouse number 7? | 4512 | code_pl, support_en, orion_en | candidate_correct_result_only | 4512 |
| qwen2.5:1.5b | closed_book | f6 | Do której godziny działa obsługa klienta Nordwind w dni robocze? | 16:45\|16.45 |  | manual_review | Do godziny 17:00 działa obsługa klienta Nordwind w dni robocze. |
| qwen2.5:1.5b | rag | f6 | Do której godziny działa obsługa klienta Nordwind w dni robocze? | 16:45\|16.45 | support_en, code_pl, fleet_en | candidate_correct | Do godziny 16:45 działa obsługa klienta Nordwind w dni robocze. |
| qwen2.5:1.5b | closed_book | g1 | Which city is the capital of Australia? | Canberra |  | candidate_correct | The capital of Australia is Canberra. |
| qwen2.5:1.5b | rag | g1 | Which city is the capital of Australia? | Canberra | canberra_pl, warsaw_en, krakow_pl | candidate_correct | Canberra |
| qwen2.5:1.5b | closed_book | g2 | Jakie miasto jest stolicą Polski? | Warszawa\|Warsaw\|Warszawie |  | candidate_correct | Stolica Polski to Warszawa. |
| qwen2.5:1.5b | rag | g2 | Jakie miasto jest stolicą Polski? | Warszawa\|Warsaw\|Warszawie | krakow_pl, warsaw_en, canberra_pl | manual_review | Kraków |
| qwen2.5:1.5b | closed_book | g3 | Where were Polish kings crowned? | Wawel\|Kraków\|Krakow\|Cracow |  | candidate_correct | Polish kings were crowned in the Basilica of the Holy Cross in Kraków. |
| qwen2.5:1.5b | rag | g3 | Where were Polish kings crowned? | Wawel\|Kraków\|Krakow\|Cracow | krakow_pl, warsaw_en, fx_en | candidate_correct | Kraków |
| qwen2.5:1.5b | closed_book | g4 | Jakim protokołem zmienia się konfigurację urządzeń sieciowych? | NETCONF |  | manual_review | Protokół DHCP (Dynamic Host Configuration Protocol) zmienia konfigurację urządzeń sieciowych. |
| qwen2.5:1.5b | rag | g4 | Jakim protokołem zmienia się konfigurację urządzeń sieciowych? | NETCONF | netconf_en, yang_pl, helm_en | candidate_correct | NETCONF |
| qwen2.5:1.5b | closed_book | g5 | What do whales feed their young with? | milk\|mleko\|mlekiem |  | candidate_correct | Whales feed their young with milk. |
| qwen2.5:1.5b | rag | g5 | What do whales feed their young with? | milk\|mleko\|mlekiem | whales_en, birds_pl, cats_en | candidate_correct | Whales feed their young with milk. |
| qwen2.5:1.5b | closed_book | g6 | Jak nazywa się narzędzie pakujące aplikacje Kubernetes w wykresy? | Helm |  | manual_review | Opracowywanie wykresów aplikacji Kubernetes jest wykonane przez narzędzie叫做 "Kubernetes Dashboard". |
| qwen2.5:1.5b | rag | g6 | Jak nazywa się narzędzie pakujące aplikacje Kubernetes w wykresy? | Helm | helm_en, yang_pl, netconf_en | manual_review | Nie wiesz. |
