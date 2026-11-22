# Tool use: which local models can drive tools

> 9 tasks per model and mode: a quick check of whether a model can drive tools, not a general agent benchmark. 'Right answer' is the rule-based screening.

## Summary

| Model | Mode | Tasks | Right tools | Right answer | Both | Valid calls | Mean steps | Not answered |
|---|---|---|---|---|---|---|---|---|
| bielik-4.5b-v3:fp16 | json | 9 | 5 | 5 | 4 | 1.0 | 1.67 | 0 |

## Every run

| Model | Mode | Task | Question | Expected tools | Tools used | Expected | Answer | Screening | Stop |
|---|---|---|---|---|---|---|---|---|---|
| bielik-4.5b-v3:fp16 | json | calc_pl | Ile wynosi 17 razy 23 razy 19? | calculator | calculator | 7429 | 17 razy 23 razy 19 wynosi 7429. | candidate_correct_result_only | answered |
| bielik-4.5b-v3:fp16 | json | calc_big_en | What is 123456 multiplied by 789? | calculator | calculator | 97406784 | The result of 123456 multiplied by 789 is 9,740,6784. | candidate_incorrect | answered |
| bielik-4.5b-v3:fp16 | json | calc_expr_en | Compute (48.5 - 12.25) / 0.25. | calculator |  | 145 | 154.5 | manual_review | answered |
| bielik-4.5b-v3:fp16 | json | convert_pl | Ile minut ma 2,5 dnia? | convert_units\|calculator | calculator | 3600 | 2,5 dnia to 3600 minut. | candidate_correct_result_only | answered |
| bielik-4.5b-v3:fp16 | json | convert_en | Convert 77 degrees Fahrenheit to Celsius. | convert_units\|calculator | convert_units | 25 | 77 degrees Fahrenheit is equal to 25 degrees Celsius. | candidate_correct_result_only | answered |
| bielik-4.5b-v3:fp16 | json | search_pl | Ile ciężarówek elektrycznych ma firma Nordwind? | search_documents | search_documents | 19 | Firma Nordwind ma 19 ciężarówek elektrycznych. | candidate_correct_result_only | answered |
| bielik-4.5b-v3:fp16 | json | search_en | What is the access code of Nordwind warehouse number 7? | search_documents |  | 4512 | I'm sorry, but I don't have access to specific information about Nordwind warehouse number 7, such as its access code. You may need to contact Nordwind or check their security system for this informat | manual_review | answered |
| bielik-4.5b-v3:fp16 | json | search_calc_en | How much does one year of the Nordwind Express subscription cost in total? | search_documents, calculator |  | 588 | I'm unable to directly access pricing information or current data. However, I can help you calculate if you provide the monthly cost. **Question:** How much does one month of the Nordwind Express subs | manual_review | answered |
| bielik-4.5b-v3:fp16 | json | no_tool_pl | Jakie miasto jest stolicą Polski? |  | search_documents | Warszawa\|Warszawie\|Warsaw | Warszawa | candidate_correct | answered |
