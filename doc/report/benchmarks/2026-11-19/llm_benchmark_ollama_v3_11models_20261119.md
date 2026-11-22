# LLM benchmark: 11 local models on Ollama (CPU), bilingual_reasoning@3 (16 tasks), max_tokens 768

> Screening is a rule-based pre-assessment, not a verdict: 'correct' and 'incorrect' are candidates, 'manual review' needs a human. Latency is wall-clock time per request after a warm-up, on this machine.

- Task set: bilingual_reasoning@3
- Provider: ollama (http://127.0.0.1:11434)
- Repeats: 2, temperature 0.0, max_tokens 768
- Run started (UTC): 2026-11-19T05:10:04.836185+00:00
- Screening version: 4.7
- Task/model cells whose runs disagree: 7

## Models by screening outcome

| Model | Lang | Answered | Requests | Median s | p90 s | Truncated | Correct | Incorrect | Partial | Manual review |
|---|---|---|---|---|---|---|---|---|---|---|
| bielik-4.5b-v3:q8_0 | en | 32 | 32 | 16.8 | 51.53 | 2 | 30 | 0 | 0 | 2 |
| gemma3:4b | en | 32 | 32 | 8.01 | 21.79 | 0 | 30 | 0 | 0 | 2 |
| bielik-11b-v2.6:q4_k_m | en | 32 | 32 | 22.82 | 70.68 | 0 | 28 | 0 | 0 | 4 |
| bielik-11b-v2.6:q4_k_m | pl | 32 | 32 | 54.3 | 103.82 | 2 | 28 | 0 | 0 | 4 |
| bielik-4.5b-v3:q8_0 | pl | 32 | 32 | 22.43 | 50.93 | 0 | 28 | 0 | 0 | 4 |
| phi3:mini | en | 32 | 32 | 5.97 | 22.53 | 0 | 28 | 0 | 0 | 4 |
| qwen2.5:1.5b | en | 32 | 32 | 3.21 | 7.57 | 0 | 28 | 0 | 0 | 4 |
| gemma3:1b | en | 32 | 32 | 2.36 | 7.25 | 0 | 26 | 0 | 0 | 6 |
| llama3.2:3b | en | 32 | 32 | 3.89 | 9.32 | 0 | 26 | 0 | 0 | 6 |
| qwen2.5:3b | en | 32 | 32 | 6.98 | 12.98 | 0 | 26 | 0 | 0 | 6 |
| qwen2.5:0.5b | en | 32 | 32 | 1.35 | 3.39 | 0 | 26 | 2 | 0 | 4 |
| bielik-1.5b-v3:q4_k_m | en | 32 | 32 | 2.87 | 10.46 | 0 | 25 | 2 | 0 | 5 |
| gemma3:4b | pl | 32 | 32 | 5.63 | 14.0 | 0 | 24 | 2 | 0 | 6 |
| llama3.2:3b | pl | 32 | 32 | 2.1 | 9.78 | 0 | 24 | 2 | 0 | 6 |
| gemma3:1b | pl | 32 | 32 | 1.7 | 3.93 | 0 | 20 | 4 | 0 | 8 |
| bielik-1.5b-v3:q4_k_m | pl | 32 | 32 | 1.26 | 5.41 | 0 | 19 | 3 | 0 | 10 |
| qwen2.5:1.5b | pl | 32 | 32 | 2.37 | 18.48 | 6 | 19 | 4 | 0 | 9 |
| llama3.2:1b | en | 32 | 32 | 1.89 | 6.67 | 0 | 18 | 0 | 0 | 14 |
| qwen2.5:3b | pl | 32 | 32 | 5.17 | 17.62 | 0 | 18 | 0 | 0 | 14 |
| phi3:mini | pl | 32 | 32 | 6.89 | 60.46 | 6 | 16 | 0 | 0 | 16 |
| llama3.2:1b | pl | 32 | 32 | 1.41 | 3.94 | 0 | 14 | 6 | 0 | 12 |
| qwen2.5:0.5b | pl | 32 | 32 | 0.38 | 4.73 | 3 | 7 | 12 | 0 | 13 |

## Warm-up

| Model | Status | Load + first answer s | Error |
|---|---|---|---|
| qwen2.5:0.5b | PASS | 1.542 |  |
| qwen2.5:1.5b | PASS | 2.829 |  |
| qwen2.5:3b | PASS | 24.572 |  |
| llama3.2:1b | PASS | 3.168 |  |
| llama3.2:3b | PASS | 81.049 |  |
| gemma3:1b | PASS | 1.758 |  |
| gemma3:4b | PASS | 39.293 |  |
| phi3:mini | PASS | 24.6 |  |
| bielik-1.5b-v3:q4_k_m | PASS | 1.99 |  |
| bielik-4.5b-v3:q8_0 | PASS | 81.465 |  |
| bielik-11b-v2.6:q4_k_m | PASS | 130.215 |  |

## Outcome per task, language and model

| Task | Lang | Model | Majority outcome | Runs agree | All runs |
|---|---|---|---|---|---|
| arithmetic_multiplication | en | bielik-1.5b-v3:q4_k_m | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| arithmetic_multiplication | en | bielik-11b-v2.6:q4_k_m | candidate_correct_with_calculation | yes | candidate_correct_with_calculation, candidate_correct_with_calculation |
| arithmetic_multiplication | en | bielik-4.5b-v3:q8_0 | candidate_correct_with_calculation | yes | candidate_correct_with_calculation, candidate_correct_with_calculation |
| arithmetic_multiplication | en | gemma3:1b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| arithmetic_multiplication | en | gemma3:4b | candidate_correct_with_calculation | yes | candidate_correct_with_calculation, candidate_correct_with_calculation |
| arithmetic_multiplication | en | llama3.2:1b | candidate_correct_with_calculation | yes | candidate_correct_with_calculation, candidate_correct_with_calculation |
| arithmetic_multiplication | en | llama3.2:3b | candidate_correct_with_calculation | yes | candidate_correct_with_calculation, candidate_correct_with_calculation |
| arithmetic_multiplication | en | phi3:mini | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| arithmetic_multiplication | en | qwen2.5:0.5b | manual_review | yes | manual_review, manual_review |
| arithmetic_multiplication | en | qwen2.5:1.5b | candidate_correct_with_calculation | no | candidate_correct_with_calculation, candidate_correct_result_only |
| arithmetic_multiplication | en | qwen2.5:3b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| arithmetic_multiplication | pl | bielik-1.5b-v3:q4_k_m | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| arithmetic_multiplication | pl | bielik-11b-v2.6:q4_k_m | candidate_correct_with_calculation | yes | candidate_correct_with_calculation, candidate_correct_with_calculation |
| arithmetic_multiplication | pl | bielik-4.5b-v3:q8_0 | candidate_correct_with_calculation | yes | candidate_correct_with_calculation, candidate_correct_with_calculation |
| arithmetic_multiplication | pl | gemma3:1b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| arithmetic_multiplication | pl | gemma3:4b | candidate_correct_with_calculation | yes | candidate_correct_with_calculation, candidate_correct_with_calculation |
| arithmetic_multiplication | pl | llama3.2:1b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| arithmetic_multiplication | pl | llama3.2:3b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| arithmetic_multiplication | pl | phi3:mini | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| arithmetic_multiplication | pl | qwen2.5:0.5b | candidate_incorrect | yes | candidate_incorrect, candidate_incorrect |
| arithmetic_multiplication | pl | qwen2.5:1.5b | candidate_correct_with_calculation | yes | candidate_correct_with_calculation, candidate_correct_with_calculation |
| arithmetic_multiplication | pl | qwen2.5:3b | candidate_correct_with_calculation | yes | candidate_correct_with_calculation, candidate_correct_with_calculation |
| capital_city | en | bielik-1.5b-v3:q4_k_m | candidate_correct | yes | candidate_correct, candidate_correct |
| capital_city | en | bielik-11b-v2.6:q4_k_m | candidate_correct | yes | candidate_correct, candidate_correct |
| capital_city | en | bielik-4.5b-v3:q8_0 | candidate_correct | yes | candidate_correct, candidate_correct |
| capital_city | en | gemma3:1b | candidate_correct | yes | candidate_correct, candidate_correct |
| capital_city | en | gemma3:4b | candidate_correct | yes | candidate_correct, candidate_correct |
| capital_city | en | llama3.2:1b | candidate_correct | yes | candidate_correct, candidate_correct |
| capital_city | en | llama3.2:3b | candidate_correct | yes | candidate_correct, candidate_correct |
| capital_city | en | phi3:mini | candidate_correct | yes | candidate_correct, candidate_correct |
| capital_city | en | qwen2.5:0.5b | candidate_correct | yes | candidate_correct, candidate_correct |
| capital_city | en | qwen2.5:1.5b | candidate_correct | yes | candidate_correct, candidate_correct |
| capital_city | en | qwen2.5:3b | candidate_correct | yes | candidate_correct, candidate_correct |
| capital_city | pl | bielik-1.5b-v3:q4_k_m | candidate_correct | yes | candidate_correct, candidate_correct |
| capital_city | pl | bielik-11b-v2.6:q4_k_m | candidate_correct | yes | candidate_correct, candidate_correct |
| capital_city | pl | bielik-4.5b-v3:q8_0 | manual_review | yes | manual_review, manual_review |
| capital_city | pl | gemma3:1b | candidate_correct | yes | candidate_correct, candidate_correct |
| capital_city | pl | gemma3:4b | candidate_correct | yes | candidate_correct, candidate_correct |
| capital_city | pl | llama3.2:1b | candidate_correct | yes | candidate_correct, candidate_correct |
| capital_city | pl | llama3.2:3b | candidate_correct | yes | candidate_correct, candidate_correct |
| capital_city | pl | phi3:mini | manual_review | yes | manual_review, manual_review |
| capital_city | pl | qwen2.5:0.5b | manual_review | yes | manual_review, manual_review |
| capital_city | pl | qwen2.5:1.5b | candidate_correct | no | candidate_correct, manual_review |
| capital_city | pl | qwen2.5:3b | manual_review | yes | manual_review, manual_review |
| currency_vs_inflation | en | bielik-1.5b-v3:q4_k_m | candidate_correct_conclusion_direction_not_assessed | yes | candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed |
| currency_vs_inflation | en | bielik-11b-v2.6:q4_k_m | candidate_correct_conclusion_direction_not_assessed | yes | candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed |
| currency_vs_inflation | en | bielik-4.5b-v3:q8_0 | candidate_correct_conclusion_direction_not_assessed | yes | candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed |
| currency_vs_inflation | en | gemma3:1b | manual_review | yes | manual_review, manual_review |
| currency_vs_inflation | en | gemma3:4b | manual_review | yes | manual_review, manual_review |
| currency_vs_inflation | en | llama3.2:1b | candidate_correct_conclusion_direction_not_assessed | yes | candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed |
| currency_vs_inflation | en | llama3.2:3b | candidate_correct_conclusion_direction_not_assessed | yes | candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed |
| currency_vs_inflation | en | phi3:mini | candidate_correct_conclusion_direction_not_assessed | yes | candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed |
| currency_vs_inflation | en | qwen2.5:0.5b | candidate_correct_conclusion_direction_not_assessed | yes | candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed |
| currency_vs_inflation | en | qwen2.5:1.5b | candidate_correct_conclusion_direction_not_assessed | yes | candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed |
| currency_vs_inflation | en | qwen2.5:3b | candidate_correct_conclusion_direction_not_assessed | yes | candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed |
| currency_vs_inflation | pl | bielik-1.5b-v3:q4_k_m | manual_review | yes | manual_review, manual_review |
| currency_vs_inflation | pl | bielik-11b-v2.6:q4_k_m | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| currency_vs_inflation | pl | bielik-4.5b-v3:q8_0 | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| currency_vs_inflation | pl | gemma3:1b | candidate_correct_conclusion_direction_not_assessed | yes | candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed |
| currency_vs_inflation | pl | gemma3:4b | candidate_correct_conclusion_direction_not_assessed | yes | candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed |
| currency_vs_inflation | pl | llama3.2:1b | manual_review | yes | manual_review, manual_review |
| currency_vs_inflation | pl | llama3.2:3b | manual_review | yes | manual_review, manual_review |
| currency_vs_inflation | pl | phi3:mini | candidate_correct_conclusion_direction_not_assessed | yes | candidate_correct_conclusion_direction_not_assessed, candidate_correct_conclusion_direction_not_assessed |
| currency_vs_inflation | pl | qwen2.5:0.5b | manual_review | yes | manual_review, manual_review |
| currency_vs_inflation | pl | qwen2.5:1.5b | candidate_incorrect_conclusion | yes | candidate_incorrect_conclusion, candidate_incorrect_conclusion |
| currency_vs_inflation | pl | qwen2.5:3b | manual_review | yes | manual_review, manual_review |
| decimal_comparison | en | bielik-1.5b-v3:q4_k_m | candidate_incorrect_conclusion | no | candidate_incorrect_conclusion, candidate_correct_conclusion |
| decimal_comparison | en | bielik-11b-v2.6:q4_k_m | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| decimal_comparison | en | bielik-4.5b-v3:q8_0 | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| decimal_comparison | en | gemma3:1b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| decimal_comparison | en | gemma3:4b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| decimal_comparison | en | llama3.2:1b | manual_review | yes | manual_review, manual_review |
| decimal_comparison | en | llama3.2:3b | manual_review | yes | manual_review, manual_review |
| decimal_comparison | en | phi3:mini | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| decimal_comparison | en | qwen2.5:0.5b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| decimal_comparison | en | qwen2.5:1.5b | manual_review | yes | manual_review, manual_review |
| decimal_comparison | en | qwen2.5:3b | manual_review | yes | manual_review, manual_review |
| decimal_comparison | pl | bielik-1.5b-v3:q4_k_m | manual_review | yes | manual_review, manual_review |
| decimal_comparison | pl | bielik-11b-v2.6:q4_k_m | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| decimal_comparison | pl | bielik-4.5b-v3:q8_0 | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| decimal_comparison | pl | gemma3:1b | candidate_incorrect_conclusion | yes | candidate_incorrect_conclusion, candidate_incorrect_conclusion |
| decimal_comparison | pl | gemma3:4b | candidate_incorrect_conclusion | yes | candidate_incorrect_conclusion, candidate_incorrect_conclusion |
| decimal_comparison | pl | llama3.2:1b | candidate_incorrect_conclusion | yes | candidate_incorrect_conclusion, candidate_incorrect_conclusion |
| decimal_comparison | pl | llama3.2:3b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| decimal_comparison | pl | phi3:mini | manual_review | yes | manual_review, manual_review |
| decimal_comparison | pl | qwen2.5:0.5b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| decimal_comparison | pl | qwen2.5:1.5b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| decimal_comparison | pl | qwen2.5:3b | manual_review | yes | manual_review, manual_review |
| division_remainder | en | bielik-1.5b-v3:q4_k_m | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| division_remainder | en | bielik-11b-v2.6:q4_k_m | manual_review | yes | manual_review, manual_review |
| division_remainder | en | bielik-4.5b-v3:q8_0 | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| division_remainder | en | gemma3:1b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| division_remainder | en | gemma3:4b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| division_remainder | en | llama3.2:1b | manual_review | yes | manual_review, manual_review |
| division_remainder | en | llama3.2:3b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| division_remainder | en | phi3:mini | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| division_remainder | en | qwen2.5:0.5b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| division_remainder | en | qwen2.5:1.5b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| division_remainder | en | qwen2.5:3b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| division_remainder | pl | bielik-1.5b-v3:q4_k_m | candidate_incorrect | yes | candidate_incorrect, candidate_incorrect |
| division_remainder | pl | bielik-11b-v2.6:q4_k_m | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| division_remainder | pl | bielik-4.5b-v3:q8_0 | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| division_remainder | pl | gemma3:1b | manual_review | yes | manual_review, manual_review |
| division_remainder | pl | gemma3:4b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| division_remainder | pl | llama3.2:1b | candidate_incorrect | yes | candidate_incorrect, candidate_incorrect |
| division_remainder | pl | llama3.2:3b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| division_remainder | pl | phi3:mini | manual_review | yes | manual_review, manual_review |
| division_remainder | pl | qwen2.5:0.5b | candidate_incorrect | yes | candidate_incorrect, candidate_incorrect |
| division_remainder | pl | qwen2.5:1.5b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| division_remainder | pl | qwen2.5:3b | manual_review | yes | manual_review, manual_review |
| letter_count | en | bielik-1.5b-v3:q4_k_m | candidate_incorrect | no | candidate_incorrect, manual_review |
| letter_count | en | bielik-11b-v2.6:q4_k_m | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| letter_count | en | bielik-4.5b-v3:q8_0 | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| letter_count | en | gemma3:1b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| letter_count | en | gemma3:4b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| letter_count | en | llama3.2:1b | manual_review | yes | manual_review, manual_review |
| letter_count | en | llama3.2:3b | manual_review | yes | manual_review, manual_review |
| letter_count | en | phi3:mini | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| letter_count | en | qwen2.5:0.5b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| letter_count | en | qwen2.5:1.5b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| letter_count | en | qwen2.5:3b | manual_review | yes | manual_review, manual_review |
| letter_count | pl | bielik-1.5b-v3:q4_k_m | manual_review | yes | manual_review, manual_review |
| letter_count | pl | bielik-11b-v2.6:q4_k_m | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| letter_count | pl | bielik-4.5b-v3:q8_0 | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| letter_count | pl | gemma3:1b | candidate_incorrect | yes | candidate_incorrect, candidate_incorrect |
| letter_count | pl | gemma3:4b | manual_review | yes | manual_review, manual_review |
| letter_count | pl | llama3.2:1b | manual_review | yes | manual_review, manual_review |
| letter_count | pl | llama3.2:3b | candidate_incorrect | yes | candidate_incorrect, candidate_incorrect |
| letter_count | pl | phi3:mini | manual_review | yes | manual_review, manual_review |
| letter_count | pl | qwen2.5:0.5b | manual_review | yes | manual_review, manual_review |
| letter_count | pl | qwen2.5:1.5b | candidate_incorrect | yes | candidate_incorrect, candidate_incorrect |
| letter_count | pl | qwen2.5:3b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| logical_syllogism | en | bielik-1.5b-v3:q4_k_m | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | en | bielik-11b-v2.6:q4_k_m | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | en | bielik-4.5b-v3:q8_0 | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | en | gemma3:1b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | en | gemma3:4b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | en | llama3.2:1b | manual_review | yes | manual_review, manual_review |
| logical_syllogism | en | llama3.2:3b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | en | phi3:mini | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | en | qwen2.5:0.5b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | en | qwen2.5:1.5b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | en | qwen2.5:3b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | pl | bielik-1.5b-v3:q4_k_m | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | pl | bielik-11b-v2.6:q4_k_m | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | pl | bielik-4.5b-v3:q8_0 | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | pl | gemma3:1b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | pl | gemma3:4b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | pl | llama3.2:1b | candidate_incorrect_conclusion | yes | candidate_incorrect_conclusion, candidate_incorrect_conclusion |
| logical_syllogism | pl | llama3.2:3b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | pl | phi3:mini | manual_review | yes | manual_review, manual_review |
| logical_syllogism | pl | qwen2.5:0.5b | candidate_incorrect_conclusion | yes | candidate_incorrect_conclusion, candidate_incorrect_conclusion |
| logical_syllogism | pl | qwen2.5:1.5b | manual_review | yes | manual_review, manual_review |
| logical_syllogism | pl | qwen2.5:3b | manual_review | yes | manual_review, manual_review |
| negated_syllogism | en | bielik-1.5b-v3:q4_k_m | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| negated_syllogism | en | bielik-11b-v2.6:q4_k_m | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| negated_syllogism | en | bielik-4.5b-v3:q8_0 | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| negated_syllogism | en | gemma3:1b | manual_review | yes | manual_review, manual_review |
| negated_syllogism | en | gemma3:4b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| negated_syllogism | en | llama3.2:1b | manual_review | yes | manual_review, manual_review |
| negated_syllogism | en | llama3.2:3b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| negated_syllogism | en | phi3:mini | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| negated_syllogism | en | qwen2.5:0.5b | candidate_incorrect_conclusion | yes | candidate_incorrect_conclusion, candidate_incorrect_conclusion |
| negated_syllogism | en | qwen2.5:1.5b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| negated_syllogism | en | qwen2.5:3b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| negated_syllogism | pl | bielik-1.5b-v3:q4_k_m | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| negated_syllogism | pl | bielik-11b-v2.6:q4_k_m | manual_review | yes | manual_review, manual_review |
| negated_syllogism | pl | bielik-4.5b-v3:q8_0 | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| negated_syllogism | pl | gemma3:1b | manual_review | yes | manual_review, manual_review |
| negated_syllogism | pl | gemma3:4b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| negated_syllogism | pl | llama3.2:1b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| negated_syllogism | pl | llama3.2:3b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| negated_syllogism | pl | phi3:mini | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| negated_syllogism | pl | qwen2.5:0.5b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| negated_syllogism | pl | qwen2.5:1.5b | manual_review | yes | manual_review, manual_review |
| negated_syllogism | pl | qwen2.5:3b | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion |
| number_sequence | en | bielik-1.5b-v3:q4_k_m | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| number_sequence | en | bielik-11b-v2.6:q4_k_m | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| number_sequence | en | bielik-4.5b-v3:q8_0 | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| number_sequence | en | gemma3:1b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| number_sequence | en | gemma3:4b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| number_sequence | en | llama3.2:1b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| number_sequence | en | llama3.2:3b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| number_sequence | en | phi3:mini | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| number_sequence | en | qwen2.5:0.5b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| number_sequence | en | qwen2.5:1.5b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| number_sequence | en | qwen2.5:3b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| number_sequence | pl | bielik-1.5b-v3:q4_k_m | candidate_incorrect | no | candidate_incorrect, manual_review |
| number_sequence | pl | bielik-11b-v2.6:q4_k_m | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| number_sequence | pl | bielik-4.5b-v3:q8_0 | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| number_sequence | pl | gemma3:1b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| number_sequence | pl | gemma3:4b | manual_review | yes | manual_review, manual_review |
| number_sequence | pl | llama3.2:1b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| number_sequence | pl | llama3.2:3b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| number_sequence | pl | phi3:mini | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| number_sequence | pl | qwen2.5:0.5b | candidate_incorrect | yes | candidate_incorrect, candidate_incorrect |
| number_sequence | pl | qwen2.5:1.5b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| number_sequence | pl | qwen2.5:3b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| percentage_change | en | bielik-1.5b-v3:q4_k_m | candidate_correct | yes | candidate_correct, candidate_correct |
| percentage_change | en | bielik-11b-v2.6:q4_k_m | candidate_correct | yes | candidate_correct, candidate_correct |
| percentage_change | en | bielik-4.5b-v3:q8_0 | candidate_correct | yes | candidate_correct, candidate_correct |
| percentage_change | en | gemma3:1b | candidate_correct | yes | candidate_correct, candidate_correct |
| percentage_change | en | gemma3:4b | candidate_correct | yes | candidate_correct, candidate_correct |
| percentage_change | en | llama3.2:1b | candidate_correct | yes | candidate_correct, candidate_correct |
| percentage_change | en | llama3.2:3b | candidate_correct | yes | candidate_correct, candidate_correct |
| percentage_change | en | phi3:mini | manual_review | yes | manual_review, manual_review |
| percentage_change | en | qwen2.5:0.5b | candidate_correct | yes | candidate_correct, candidate_correct |
| percentage_change | en | qwen2.5:1.5b | candidate_correct | yes | candidate_correct, candidate_correct |
| percentage_change | en | qwen2.5:3b | candidate_correct | yes | candidate_correct, candidate_correct |
| percentage_change | pl | bielik-1.5b-v3:q4_k_m | candidate_correct | yes | candidate_correct, candidate_correct |
| percentage_change | pl | bielik-11b-v2.6:q4_k_m | candidate_correct | yes | candidate_correct, candidate_correct |
| percentage_change | pl | bielik-4.5b-v3:q8_0 | candidate_correct | yes | candidate_correct, candidate_correct |
| percentage_change | pl | gemma3:1b | manual_review | yes | manual_review, manual_review |
| percentage_change | pl | gemma3:4b | candidate_correct | yes | candidate_correct, candidate_correct |
| percentage_change | pl | llama3.2:1b | manual_review | yes | manual_review, manual_review |
| percentage_change | pl | llama3.2:3b | candidate_correct | yes | candidate_correct, candidate_correct |
| percentage_change | pl | phi3:mini | candidate_correct | yes | candidate_correct, candidate_correct |
| percentage_change | pl | qwen2.5:0.5b | candidate_correct | no | candidate_correct, manual_review |
| percentage_change | pl | qwen2.5:1.5b | candidate_correct | yes | candidate_correct, candidate_correct |
| percentage_change | pl | qwen2.5:3b | candidate_correct | yes | candidate_correct, candidate_correct |
| percentage_of | en | bielik-1.5b-v3:q4_k_m | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| percentage_of | en | bielik-11b-v2.6:q4_k_m | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| percentage_of | en | bielik-4.5b-v3:q8_0 | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| percentage_of | en | gemma3:1b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| percentage_of | en | gemma3:4b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| percentage_of | en | llama3.2:1b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| percentage_of | en | llama3.2:3b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| percentage_of | en | phi3:mini | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| percentage_of | en | qwen2.5:0.5b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| percentage_of | en | qwen2.5:1.5b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| percentage_of | en | qwen2.5:3b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| percentage_of | pl | bielik-1.5b-v3:q4_k_m | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| percentage_of | pl | bielik-11b-v2.6:q4_k_m | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| percentage_of | pl | bielik-4.5b-v3:q8_0 | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| percentage_of | pl | gemma3:1b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| percentage_of | pl | gemma3:4b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| percentage_of | pl | llama3.2:1b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| percentage_of | pl | llama3.2:3b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| percentage_of | pl | phi3:mini | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| percentage_of | pl | qwen2.5:0.5b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| percentage_of | pl | qwen2.5:1.5b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| percentage_of | pl | qwen2.5:3b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| plural_form | en | bielik-1.5b-v3:q4_k_m | manual_review | yes | manual_review, manual_review |
| plural_form | en | bielik-11b-v2.6:q4_k_m | candidate_correct | yes | candidate_correct, candidate_correct |
| plural_form | en | bielik-4.5b-v3:q8_0 | candidate_correct | yes | candidate_correct, candidate_correct |
| plural_form | en | gemma3:1b | candidate_correct | yes | candidate_correct, candidate_correct |
| plural_form | en | gemma3:4b | candidate_correct | yes | candidate_correct, candidate_correct |
| plural_form | en | llama3.2:1b | candidate_correct | yes | candidate_correct, candidate_correct |
| plural_form | en | llama3.2:3b | candidate_correct | yes | candidate_correct, candidate_correct |
| plural_form | en | phi3:mini | candidate_correct | yes | candidate_correct, candidate_correct |
| plural_form | en | qwen2.5:0.5b | candidate_correct | yes | candidate_correct, candidate_correct |
| plural_form | en | qwen2.5:1.5b | candidate_correct | yes | candidate_correct, candidate_correct |
| plural_form | en | qwen2.5:3b | candidate_correct | yes | candidate_correct, candidate_correct |
| plural_form | pl | bielik-1.5b-v3:q4_k_m | manual_review | no | manual_review, candidate_correct |
| plural_form | pl | bielik-11b-v2.6:q4_k_m | candidate_correct | yes | candidate_correct, candidate_correct |
| plural_form | pl | bielik-4.5b-v3:q8_0 | candidate_correct | yes | candidate_correct, candidate_correct |
| plural_form | pl | gemma3:1b | manual_review | yes | manual_review, manual_review |
| plural_form | pl | gemma3:4b | candidate_correct | yes | candidate_correct, candidate_correct |
| plural_form | pl | llama3.2:1b | manual_review | yes | manual_review, manual_review |
| plural_form | pl | llama3.2:3b | manual_review | yes | manual_review, manual_review |
| plural_form | pl | phi3:mini | manual_review | yes | manual_review, manual_review |
| plural_form | pl | qwen2.5:0.5b | manual_review | yes | manual_review, manual_review |
| plural_form | pl | qwen2.5:1.5b | manual_review | yes | manual_review, manual_review |
| plural_form | pl | qwen2.5:3b | manual_review | yes | manual_review, manual_review |
| time_arithmetic | en | bielik-1.5b-v3:q4_k_m | candidate_correct | yes | candidate_correct, candidate_correct |
| time_arithmetic | en | bielik-11b-v2.6:q4_k_m | candidate_correct | yes | candidate_correct, candidate_correct |
| time_arithmetic | en | bielik-4.5b-v3:q8_0 | candidate_correct | yes | candidate_correct, candidate_correct |
| time_arithmetic | en | gemma3:1b | candidate_correct | yes | candidate_correct, candidate_correct |
| time_arithmetic | en | gemma3:4b | candidate_correct | yes | candidate_correct, candidate_correct |
| time_arithmetic | en | llama3.2:1b | manual_review | yes | manual_review, manual_review |
| time_arithmetic | en | llama3.2:3b | candidate_correct | yes | candidate_correct, candidate_correct |
| time_arithmetic | en | phi3:mini | candidate_correct | yes | candidate_correct, candidate_correct |
| time_arithmetic | en | qwen2.5:0.5b | candidate_correct | yes | candidate_correct, candidate_correct |
| time_arithmetic | en | qwen2.5:1.5b | candidate_correct | yes | candidate_correct, candidate_correct |
| time_arithmetic | en | qwen2.5:3b | candidate_correct | yes | candidate_correct, candidate_correct |
| time_arithmetic | pl | bielik-1.5b-v3:q4_k_m | candidate_correct | yes | candidate_correct, candidate_correct |
| time_arithmetic | pl | bielik-11b-v2.6:q4_k_m | candidate_correct | yes | candidate_correct, candidate_correct |
| time_arithmetic | pl | bielik-4.5b-v3:q8_0 | candidate_correct | yes | candidate_correct, candidate_correct |
| time_arithmetic | pl | gemma3:1b | candidate_correct | yes | candidate_correct, candidate_correct |
| time_arithmetic | pl | gemma3:4b | candidate_correct | yes | candidate_correct, candidate_correct |
| time_arithmetic | pl | llama3.2:1b | candidate_correct | yes | candidate_correct, candidate_correct |
| time_arithmetic | pl | llama3.2:3b | candidate_correct | yes | candidate_correct, candidate_correct |
| time_arithmetic | pl | phi3:mini | candidate_correct | yes | candidate_correct, candidate_correct |
| time_arithmetic | pl | qwen2.5:0.5b | manual_review | yes | manual_review, manual_review |
| time_arithmetic | pl | qwen2.5:1.5b | candidate_correct | yes | candidate_correct, candidate_correct |
| time_arithmetic | pl | qwen2.5:3b | candidate_correct | yes | candidate_correct, candidate_correct |
| unit_conversion | en | bielik-1.5b-v3:q4_k_m | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| unit_conversion | en | bielik-11b-v2.6:q4_k_m | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| unit_conversion | en | bielik-4.5b-v3:q8_0 | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| unit_conversion | en | gemma3:1b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| unit_conversion | en | gemma3:4b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| unit_conversion | en | llama3.2:1b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| unit_conversion | en | llama3.2:3b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| unit_conversion | en | phi3:mini | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| unit_conversion | en | qwen2.5:0.5b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| unit_conversion | en | qwen2.5:1.5b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| unit_conversion | en | qwen2.5:3b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| unit_conversion | pl | bielik-1.5b-v3:q4_k_m | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| unit_conversion | pl | bielik-11b-v2.6:q4_k_m | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| unit_conversion | pl | bielik-4.5b-v3:q8_0 | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| unit_conversion | pl | gemma3:1b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| unit_conversion | pl | gemma3:4b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| unit_conversion | pl | llama3.2:1b | manual_review | yes | manual_review, manual_review |
| unit_conversion | pl | llama3.2:3b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| unit_conversion | pl | phi3:mini | manual_review | yes | manual_review, manual_review |
| unit_conversion | pl | qwen2.5:0.5b | candidate_incorrect | yes | candidate_incorrect, candidate_incorrect |
| unit_conversion | pl | qwen2.5:1.5b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| unit_conversion | pl | qwen2.5:3b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| weekday | en | bielik-1.5b-v3:q4_k_m | manual_review | yes | manual_review, manual_review |
| weekday | en | bielik-11b-v2.6:q4_k_m | manual_review | yes | manual_review, manual_review |
| weekday | en | bielik-4.5b-v3:q8_0 | manual_review | yes | manual_review, manual_review |
| weekday | en | gemma3:1b | manual_review | yes | manual_review, manual_review |
| weekday | en | gemma3:4b | candidate_correct | yes | candidate_correct, candidate_correct |
| weekday | en | llama3.2:1b | manual_review | yes | manual_review, manual_review |
| weekday | en | llama3.2:3b | manual_review | yes | manual_review, manual_review |
| weekday | en | phi3:mini | manual_review | yes | manual_review, manual_review |
| weekday | en | qwen2.5:0.5b | manual_review | yes | manual_review, manual_review |
| weekday | en | qwen2.5:1.5b | manual_review | yes | manual_review, manual_review |
| weekday | en | qwen2.5:3b | manual_review | yes | manual_review, manual_review |
| weekday | pl | bielik-1.5b-v3:q4_k_m | manual_review | yes | manual_review, manual_review |
| weekday | pl | bielik-11b-v2.6:q4_k_m | manual_review | yes | manual_review, manual_review |
| weekday | pl | bielik-4.5b-v3:q8_0 | manual_review | yes | manual_review, manual_review |
| weekday | pl | gemma3:1b | candidate_correct | yes | candidate_correct, candidate_correct |
| weekday | pl | gemma3:4b | manual_review | yes | manual_review, manual_review |
| weekday | pl | llama3.2:1b | manual_review | yes | manual_review, manual_review |
| weekday | pl | llama3.2:3b | manual_review | yes | manual_review, manual_review |
| weekday | pl | phi3:mini | manual_review | yes | manual_review, manual_review |
| weekday | pl | qwen2.5:0.5b | manual_review | yes | manual_review, manual_review |
| weekday | pl | qwen2.5:1.5b | manual_review | yes | manual_review, manual_review |
| weekday | pl | qwen2.5:3b | manual_review | yes | manual_review, manual_review |
| word_problem | en | bielik-1.5b-v3:q4_k_m | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| word_problem | en | bielik-11b-v2.6:q4_k_m | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| word_problem | en | bielik-4.5b-v3:q8_0 | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| word_problem | en | gemma3:1b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| word_problem | en | gemma3:4b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| word_problem | en | llama3.2:1b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| word_problem | en | llama3.2:3b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| word_problem | en | phi3:mini | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| word_problem | en | qwen2.5:0.5b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| word_problem | en | qwen2.5:1.5b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| word_problem | en | qwen2.5:3b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| word_problem | pl | bielik-1.5b-v3:q4_k_m | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| word_problem | pl | bielik-11b-v2.6:q4_k_m | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| word_problem | pl | bielik-4.5b-v3:q8_0 | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| word_problem | pl | gemma3:1b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| word_problem | pl | gemma3:4b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| word_problem | pl | llama3.2:1b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| word_problem | pl | llama3.2:3b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| word_problem | pl | phi3:mini | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| word_problem | pl | qwen2.5:0.5b | candidate_incorrect | yes | candidate_incorrect, candidate_incorrect |
| word_problem | pl | qwen2.5:1.5b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
| word_problem | pl | qwen2.5:3b | candidate_correct_result_only | yes | candidate_correct_result_only, candidate_correct_result_only |
