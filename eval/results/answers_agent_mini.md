# Answers: agent / mini (42 golden questions)

Models {'planner': 'gpt-5-mini', 'answer': 'gpt-5-mini', 'grader': 'gpt-5-mini', 'judge': 'gpt-5-mini'}, index `golden__large`, commit `8266f1d`.

| slice | n | correct | status_correct | contains | f1 | judge_correct | supported_claims | evidence_recall | citation_precision | citation_recall | llm_calls | latency_ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all | 42 | 0.809 | 0.881 | 0.750 | 0.388 | 0.833 | 0.978 | 0.963 | 0.809 | 0.940 | 5.667 | 3859 |
| bridge | 9 | 0.778 | 1.000 | 0.667 | 0.578 | 0.778 | 0.963 | 0.944 | 0.907 | 0.889 | 5.444 | 3502 |
| comparison | 8 | 0.750 | 0.875 | 0.625 | 0.269 | 0.875 | 1.000 | 1.000 | 0.938 | 1.000 | 5.500 | 3392 |
| contradictory | 6 | 0.667 | 0.667 | 0.500 | 0.074 | 0.500 | 1.000 | 0.917 | 0.639 | 0.917 | 6.333 | 4239 |
| injection | 4 | 1.000 | 1.000 | 1.000 | 0.505 | 1.000 | 1.000 | 0.917 | 0.938 | 0.833 | 5.500 | 6547 |
| simple | 9 | 1.000 | 1.000 | 1.000 | 0.461 | 1.000 | 1.000 | 1.000 | 0.833 | 1.000 | 5.000 | 2090 |
| unanswerable | 6 | 0.667 | 0.667 | – | – | – | 0.750 | – | 0.000 | – | 6.667 | 5501 |

Refusal precision 1.000, recall 0.667 (4 refused, 6 should be).
Totals: 238 LLM calls, 260557 input / 25900 output tokens, $0.003206 generation + $0.000628 judge; 0 answers used the fallback.
