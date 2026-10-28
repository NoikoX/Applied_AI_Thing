# Answers: baseline / nano (42 golden questions)

Models {'planner': 'gpt-5-nano', 'answer': 'gpt-5-nano', 'grader': 'gpt-5-nano', 'judge': 'gpt-5-mini'}, index `golden__large`, commit `8266f1d`.

| slice | n | correct | status_correct | contains | f1 | judge_correct | supported_claims | evidence_recall | citation_precision | citation_recall | llm_calls | latency_ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all | 42 | 0.476 | 0.476 | 0.867 | 0.806 | 1.000 | 1.000 | 0.931 | 0.900 | 0.933 | 0.952 | 2157 |
| bridge | 9 | 0.333 | 0.333 | 0.667 | 0.821 | 1.000 | 1.000 | 0.889 | 1.000 | 0.833 | 1.000 | 2381 |
| comparison | 8 | 0.375 | 0.375 | 1.000 | 0.778 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 2211 |
| contradictory | 6 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.750 | 0.500 | 0.500 | 1.000 | 2052 |
| injection | 4 | 0.000 | 0.000 | – | – | – | – | 1.000 | – | – | 1.000 | 1912 |
| simple | 9 | 0.889 | 0.889 | 0.875 | 0.786 | 1.000 | 1.000 | 1.000 | 0.875 | 1.000 | 1.000 | 1916 |
| unanswerable | 6 | 1.000 | 1.000 | – | – | – | – | – | – | – | 0.667 | 2380 |

Refusal precision 0.222, recall 1.000 (27 refused, 6 should be).
Totals: 40 LLM calls, 69856 input / 3309 output tokens, $0.0 generation + $0.0 judge; 0 answers used the fallback.
