# LLM benchmark: 11 local models on Ollama (CPU), bilingual_reasoning@2, max_tokens 384

> Screening is a rule-based pre-assessment, not a verdict: 'correct' and 'incorrect' are candidates, 'manual review' needs a human. Latency is wall-clock time per request after a warm-up, on this machine.

- Task set: bilingual_reasoning@2
- Provider: ollama (http://127.0.0.1:11434)
- Repeats: 3, temperature 0.0, max_tokens 384
- Run started (UTC): 2026-11-19T01:29:23.395757+00:00
- Screening version: 4.6
- Task/model cells whose runs disagree: 2

## Models by screening outcome

| Model | Lang | Answered | Requests | Median s | p90 s | Truncated | Correct | Incorrect | Partial | Manual review |
|---|---|---|---|---|---|---|---|---|---|---|
| bielik-1.5b-v3:q4_k_m | en | 12 | 12 | 3.57 | 10.47 | 0 | 12 | 0 | 0 | 0 |
| bielik-11b-v2.6:q4_k_m | en | 12 | 12 | 28.58 | 54.68 | 0 | 12 | 0 | 0 | 0 |
| bielik-4.5b-v3:q8_0 | en | 12 | 12 | 39.31 | 52.24 | 0 | 12 | 0 | 0 | 0 |
| bielik-4.5b-v3:q8_0 | pl | 12 | 12 | 31.47 | 47.86 | 0 | 12 | 0 | 0 | 0 |
| gemma3:4b | pl | 12 | 12 | 12.76 | 17.33 | 0 | 12 | 0 | 0 | 0 |
| llama3.2:3b | en | 12 | 12 | 7.91 | 9.31 | 0 | 12 | 0 | 0 | 0 |
| qwen2.5:3b | en | 12 | 12 | 6.56 | 9.14 | 0 | 12 | 0 | 0 | 0 |
| bielik-1.5b-v3:q4_k_m | pl | 12 | 12 | 4.63 | 8.25 | 0 | 9 | 0 | 0 | 3 |
| gemma3:1b | en | 12 | 12 | 4.06 | 9.8 | 3 | 9 | 0 | 0 | 3 |
| llama3.2:1b | en | 12 | 12 | 4.1 | 8.57 | 0 | 9 | 0 | 0 | 3 |
| llama3.2:3b | pl | 12 | 12 | 8.71 | 15.23 | 0 | 9 | 0 | 0 | 3 |
| phi3:mini | en | 12 | 12 | 9.28 | 21.97 | 0 | 9 | 0 | 0 | 3 |
| phi3:mini | pl | 12 | 12 | 8.78 | 24.61 | 0 | 9 | 0 | 0 | 3 |
| qwen2.5:0.5b | en | 12 | 12 | 2.52 | 3.11 | 0 | 9 | 0 | 0 | 3 |
| qwen2.5:1.5b | en | 12 | 12 | 3.83 | 8.55 | 3 | 9 | 0 | 0 | 3 |
| gemma3:1b | pl | 12 | 12 | 3.18 | 9.79 | 3 | 6 | 0 | 0 | 6 |
| gemma3:4b | en | 12 | 12 | 16.2 | 28.77 | 3 | 6 | 0 | 0 | 6 |
| qwen2.5:3b | pl | 12 | 12 | 9.63 | 15.97 | 0 | 6 | 0 | 0 | 6 |
| qwen2.5:1.5b | pl | 12 | 12 | 3.91 | 8.68 | 3 | 6 | 3 | 0 | 3 |
| qwen2.5:0.5b | pl | 12 | 12 | 2.18 | 3.85 | 3 | 5 | 4 | 0 | 3 |
| bielik-11b-v2.6:q4_k_m | pl | 12 | 12 | 73.13 | 76.16 | 9 | 3 | 0 | 0 | 9 |
| llama3.2:1b | pl | 12 | 12 | 1.1 | 13.17 | 0 | 3 | 3 | 0 | 6 |

## Warm-up

| Model | Status | Load + first answer s | Error |
|---|---|---|---|
| qwen2.5:0.5b | PASS | 3.838 |  |
| qwen2.5:1.5b | PASS | 12.723 |  |
| qwen2.5:3b | PASS | 20.853 |  |
| llama3.2:1b | PASS | 6.134 |  |
| llama3.2:3b | PASS | 41.787 |  |
| gemma3:1b | PASS | 2.28 |  |
| gemma3:4b | PASS | 53.64 |  |
| phi3:mini | PASS | 23.848 |  |
| bielik-1.5b-v3:q4_k_m | PASS | 2.782 |  |
| bielik-4.5b-v3:q8_0 | PASS | 10.204 |  |
| bielik-11b-v2.6:q4_k_m | PASS | 102.607 |  |

## Outcome per task, language and model

| Task | Lang | Model | Majority outcome | Runs agree | All runs |
|---|---|---|---|---|---|
| arithmetic_multiplication | en | bielik-1.5b-v3:q4_k_m | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only, candidate_correct_result_only |
| arithmetic_multiplication | en | bielik-11b-v2.6:q4_k_m | candidate_correct_with_calculation | yes | candidate_correct_with_calculation, candidate_correct_with_calculation, candidate_correct_with_calculation |
| arithmetic_multiplication | en | bielik-4.5b-v3:q8_0 | candidate_correct_with_calculation | yes | candidate_correct_with_calculation, candidate_correct_with_calculation, candidate_correct_with_calculation |
| arithmetic_multiplication | en | gemma3:1b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only, candidate_correct_result_only |
| arithmetic_multiplication | en | gemma3:4b | manual_review | yes | manual_review, manual_review, manual_review |
| arithmetic_multiplication | en | llama3.2:1b | candidate_correct_with_calculation | yes | candidate_correct_with_calculation, candidate_correct_with_calculation, candidate_correct_with_calculation |
| arithmetic_multiplication | en | llama3.2:3b | candidate_correct_with_calculation | yes | candidate_correct_with_calculation, candidate_correct_with_calculation, candidate_correct_with_calculation |
| arithmetic_multiplication | en | phi3:mini | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only, candidate_correct_result_only |
| arithmetic_multiplication | en | qwen2.5:0.5b | manual_review | yes | manual_review, manual_review, manual_review |
| arithmetic_multiplication | en | qwen2.5:1.5b | candidate_correct_with_calculation | yes | candidate_correct_with_calculation, candidate_correct_with_calculation, candidate_correct_with_calculation |
| arithmetic_multiplication | en | qwen2.5:3b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only, candidate_correct_result_only |
| arithmetic_multiplication | pl | bielik-1.5b-v3:q4_k_m | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only, candidate_correct_result_only |
| arithmetic_multiplication | pl | bielik-11b-v2.6:q4_k_m | candidate_correct_with_calculation | yes | candidate_correct_with_calculation, candidate_correct_with_calculation, candidate_correct_with_calculation |
| arithmetic_multiplication | pl | bielik-4.5b-v3:q8_0 | candidate_correct_with_calculation | yes | candidate_correct_with_calculation, candidate_correct_with_calculation, candidate_correct_with_calculation |
| arithmetic_multiplication | pl | gemma3:1b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only, candidate_correct_result_only |
| arithmetic_multiplication | pl | gemma3:4b | candidate_correct_with_calculation | yes | candidate_correct_with_calculation, candidate_correct_with_calculation, candidate_correct_with_calculation |
| arithmetic_multiplication | pl | llama3.2:1b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only, candidate_correct_result_only |
| arithmetic_multiplication | pl | llama3.2:3b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only, candidate_correct_result_only |
| arithmetic_multiplication | pl | phi3:mini | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only, candidate_correct_result_only |
| arithmetic_multiplication | pl | qwen2.5:0.5b | candidate_correct_result_only | no | candidate_incorrect, candidate_correct_result_only, candidate_correct_result_only |
| arithmetic_multiplication | pl | qwen2.5:1.5b | candidate_correct_with_calculation | yes | candidate_correct_with_calculation, candidate_correct_with_calculation, candidate_correct_with_calculation |
| arithmetic_multiplication | pl | qwen2.5:3b | candidate_correct_result_only | no | candidate_correct_with_calculation, candidate_correct_result_only, candidate_correct_result_only |
| currency_vs_inflation | en | bielik-1.5b-v3:q4_k_m | candidate_correct_conclusion_direction_not_assessed | yes | candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed |
| currency_vs_inflation | en | bielik-11b-v2.6:q4_k_m | candidate_correct_conclusion_direction_not_assessed | yes | candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed |
| currency_vs_inflation | en | bielik-4.5b-v3:q8_0 | candidate_correct_conclusion_direction_not_assessed | yes | candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed |
| currency_vs_inflation | en | gemma3:1b | manual_review | yes | manual_review, manual_review, manual_review |
| currency_vs_inflation | en | gemma3:4b | manual_review | yes | manual_review, manual_review, manual_review |
| currency_vs_inflation | en | llama3.2:1b | candidate_correct_conclusion_direction_not_assessed | yes | candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed |
| currency_vs_inflation | en | llama3.2:3b | candidate_correct_conclusion_direction_not_assessed | yes | candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed |
| currency_vs_inflation | en | phi3:mini | candidate_correct_conclusion_direction_not_assessed | yes | candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed |
| currency_vs_inflation | en | qwen2.5:0.5b | candidate_correct_conclusion_direction_not_assessed | yes | candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed |
| currency_vs_inflation | en | qwen2.5:1.5b | manual_review | yes | manual_review, manual_review, manual_review |
| currency_vs_inflation | en | qwen2.5:3b | candidate_correct_conclusion_direction_not_assessed | yes | candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed |
| currency_vs_inflation | pl | bielik-1.5b-v3:q4_k_m | manual_review | yes | manual_review, manual_review, manual_review |
| currency_vs_inflation | pl | bielik-11b-v2.6:q4_k_m | manual_review | yes | manual_review, manual_review, manual_review |
| currency_vs_inflation | pl | bielik-4.5b-v3:q8_0 | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion, candidate_correct_conclusion |
| currency_vs_inflation | pl | gemma3:1b | manual_review | yes | manual_review, manual_review, manual_review |
| currency_vs_inflation | pl | gemma3:4b | candidate_correct_conclusion_direction_not_assessed | yes | candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed |
| currency_vs_inflation | pl | llama3.2:1b | manual_review | yes | manual_review, manual_review, manual_review |
| currency_vs_inflation | pl | llama3.2:3b | manual_review | yes | manual_review, manual_review, manual_review |
| currency_vs_inflation | pl | phi3:mini | candidate_correct_conclusion_direction_not_assessed | yes | candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed |
| currency_vs_inflation | pl | qwen2.5:0.5b | manual_review | yes | manual_review, manual_review, manual_review |
| currency_vs_inflation | pl | qwen2.5:1.5b | candidate_incorrect_conclusion | yes | candidate_incorrect_conclusion, candidate_incorrect_conclusion, candidate_incorrect_conclusion |
| currency_vs_inflation | pl | qwen2.5:3b | manual_review | yes | manual_review, manual_review, manual_review |
| logical_syllogism | en | bielik-1.5b-v3:q4_k_m | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | en | bielik-11b-v2.6:q4_k_m | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | en | bielik-4.5b-v3:q8_0 | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | en | gemma3:1b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | en | gemma3:4b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | en | llama3.2:1b | manual_review | yes | manual_review, manual_review, manual_review |
| logical_syllogism | en | llama3.2:3b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | en | phi3:mini | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | en | qwen2.5:0.5b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | en | qwen2.5:1.5b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | en | qwen2.5:3b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | pl | bielik-1.5b-v3:q4_k_m | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | pl | bielik-11b-v2.6:q4_k_m | manual_review | yes | manual_review, manual_review, manual_review |
| logical_syllogism | pl | bielik-4.5b-v3:q8_0 | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | pl | gemma3:1b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | pl | gemma3:4b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | pl | llama3.2:1b | candidate_incorrect_conclusion | yes | candidate_incorrect_conclusion, candidate_incorrect_conclusion, candidate_incorrect_conclusion |
| logical_syllogism | pl | llama3.2:3b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | pl | phi3:mini | manual_review | yes | manual_review, manual_review, manual_review |
| logical_syllogism | pl | qwen2.5:0.5b | candidate_incorrect_conclusion | yes | candidate_incorrect_conclusion, candidate_incorrect_conclusion, candidate_incorrect_conclusion |
| logical_syllogism | pl | qwen2.5:1.5b | manual_review | yes | manual_review, manual_review, manual_review |
| logical_syllogism | pl | qwen2.5:3b | manual_review | yes | manual_review, manual_review, manual_review |
| percentage_change | en | bielik-1.5b-v3:q4_k_m | candidate_correct | yes | candidate_correct, candidate_correct, candidate_correct |
| percentage_change | en | bielik-11b-v2.6:q4_k_m | candidate_correct | yes | candidate_correct, candidate_correct, candidate_correct |
| percentage_change | en | bielik-4.5b-v3:q8_0 | candidate_correct | yes | candidate_correct, candidate_correct, candidate_correct |
| percentage_change | en | gemma3:1b | candidate_correct | yes | candidate_correct, candidate_correct, candidate_correct |
| percentage_change | en | gemma3:4b | candidate_correct | yes | candidate_correct, candidate_correct, candidate_correct |
| percentage_change | en | llama3.2:1b | candidate_correct | yes | candidate_correct, candidate_correct, candidate_correct |
| percentage_change | en | llama3.2:3b | candidate_correct | yes | candidate_correct, candidate_correct, candidate_correct |
| percentage_change | en | phi3:mini | manual_review | yes | manual_review, manual_review, manual_review |
| percentage_change | en | qwen2.5:0.5b | candidate_correct | yes | candidate_correct, candidate_correct, candidate_correct |
| percentage_change | en | qwen2.5:1.5b | candidate_correct | yes | candidate_correct, candidate_correct, candidate_correct |
| percentage_change | en | qwen2.5:3b | candidate_correct | yes | candidate_correct, candidate_correct, candidate_correct |
| percentage_change | pl | bielik-1.5b-v3:q4_k_m | candidate_correct | yes | candidate_correct, candidate_correct, candidate_correct |
| percentage_change | pl | bielik-11b-v2.6:q4_k_m | manual_review | yes | manual_review, manual_review, manual_review |
| percentage_change | pl | bielik-4.5b-v3:q8_0 | candidate_correct | yes | candidate_correct, candidate_correct, candidate_correct |
| percentage_change | pl | gemma3:1b | manual_review | yes | manual_review, manual_review, manual_review |
| percentage_change | pl | gemma3:4b | candidate_correct | yes | candidate_correct, candidate_correct, candidate_correct |
| percentage_change | pl | llama3.2:1b | manual_review | yes | manual_review, manual_review, manual_review |
| percentage_change | pl | llama3.2:3b | candidate_correct | yes | candidate_correct, candidate_correct, candidate_correct |
| percentage_change | pl | phi3:mini | candidate_correct | yes | candidate_correct, candidate_correct, candidate_correct |
| percentage_change | pl | qwen2.5:0.5b | candidate_correct | yes | candidate_correct, candidate_correct, candidate_correct |
| percentage_change | pl | qwen2.5:1.5b | candidate_correct | yes | candidate_correct, candidate_correct, candidate_correct |
| percentage_change | pl | qwen2.5:3b | candidate_correct | yes | candidate_correct, candidate_correct, candidate_correct |
