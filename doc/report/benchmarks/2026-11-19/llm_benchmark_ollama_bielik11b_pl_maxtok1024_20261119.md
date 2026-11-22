# Bielik 11B v2.6, Polish, max_tokens 1024 (supplement)

> Screening is a rule-based pre-assessment, not a verdict: 'correct' and 'incorrect' are candidates, 'manual review' needs a human. Latency is wall-clock time per request after a warm-up, on this machine.

- Task set: bilingual_reasoning@2
- Provider: ollama (http://127.0.0.1:11434)
- Repeats: 3, temperature 0.0, max_tokens 1024
- Run started (UTC): 2026-11-19T03:44:21.590354+00:00
- Screening version: 4.6
- Task/model cells whose runs disagree: 0

## Models by screening outcome

| Model | Lang | Answered | Requests | Median s | p90 s | Truncated | Correct | Incorrect | Partial | Manual review |
|---|---|---|---|---|---|---|---|---|---|---|
| bielik-11b-v2.6:q4_k_m | pl | 12 | 12 | 75.32 | 118.25 | 0 | 12 | 0 | 0 | 0 |

## Warm-up

| Model | Status | Load + first answer s | Error |
|---|---|---|---|
| bielik-11b-v2.6:q4_k_m | PASS | 28.294 |  |

## Outcome per task, language and model

| Task | Lang | Model | Majority outcome | Runs agree | All runs |
|---|---|---|---|---|---|
| arithmetic_multiplication | pl | bielik-11b-v2.6:q4_k_m | candidate_correct_with_calculation | yes | candidate_correct_with_calculation, candidate_correct_with_calculation, candidate_correct_with_calculation |
| currency_vs_inflation | pl | bielik-11b-v2.6:q4_k_m | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion, candidate_correct_conclusion |
| logical_syllogism | pl | bielik-11b-v2.6:q4_k_m | candidate_correct_conclusion | yes | candidate_correct_conclusion, candidate_correct_conclusion, candidate_correct_conclusion |
| percentage_change | pl | bielik-11b-v2.6:q4_k_m | candidate_correct | yes | candidate_correct, candidate_correct, candidate_correct |
