# Answers: baseline / gemini (42 golden questions)

Models {'planner': 'gemini-3.5-flash-lite', 'answer': 'gemini-3.5-flash-lite', 'grader': 'gemini-3.1-flash-lite', 'judge': 'gpt-5-mini'}, index `golden__large`, commit `8266f1d`.

| slice | n | correct | status_correct | contains | f1 | judge_correct | supported_claims | evidence_recall | citation_precision | citation_recall | llm_calls | latency_ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all | 42 | 0.929 | 0.929 | 0.909 | 0.262 | 1.000 | 1.000 | 0.931 | 0.934 | 0.950 | 0.952 | 2200 |
| bridge | 9 | 0.889 | 0.889 | 0.875 | 0.398 | 1.000 | 1.000 | 0.889 | 0.917 | 0.875 | 1.000 | 2299 |
| comparison | 8 | 1.000 | 1.000 | 0.750 | 0.178 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 2111 |
| contradictory | 6 | 0.667 | 0.667 | 1.000 | 0.074 | 1.000 | 1.000 | 0.750 | 0.833 | 1.000 | 1.000 | 2040 |
| injection | 4 | 1.000 | 1.000 | 1.000 | 0.209 | 1.000 | 1.000 | 1.000 | 0.917 | 0.833 | 1.000 | 2087 |
| simple | 9 | 1.000 | 1.000 | 1.000 | 0.324 | 1.000 | 1.000 | 1.000 | 0.944 | 1.000 | 1.000 | 2341 |
| unanswerable | 6 | 1.000 | 1.000 | – | – | – | – | – | – | – | 0.667 | 2192 |

Refusal precision 0.667, recall 1.000 (9 refused, 6 should be).
Totals: 40 LLM calls, 63258 input / 5068 output tokens, $0.0 generation + $0.0 judge; 0 answers used the fallback.
