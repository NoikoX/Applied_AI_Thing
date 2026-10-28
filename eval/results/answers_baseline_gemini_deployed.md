# Answers: baseline / gemini (42 golden questions)

Models {'planner': 'gemini-3.5-flash-lite', 'answer': 'gemini-3.5-flash-lite', 'grader': 'gemini-3.1-flash-lite', 'judge': 'gpt-5-mini'}, index `golden__large`, commit `1d14df9`.

| slice | n | correct | status_correct | contains | f1 | judge_correct | supported_claims | evidence_recall | citation_precision | citation_recall | llm_calls | latency_ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all | 42 | 0.929 | 0.952 | 0.882 | 0.225 | 0.941 | 1.000 | 0.921 | 0.907 | 0.917 | 1.000 | 16556 |
| bridge | 9 | 0.889 | 1.000 | 0.778 | 0.252 | 0.889 | 1.000 | 0.889 | 0.907 | 0.833 | 1.000 | 15563 |
| comparison | 8 | 1.000 | 1.000 | 0.750 | 0.177 | 1.000 | 1.000 | 1.000 | 0.938 | 1.000 | 1.000 | 13958 |
| contradictory | 6 | 0.667 | 0.667 | 1.000 | 0.077 | 0.750 | 1.000 | 0.750 | 0.750 | 1.000 | 1.000 | 20808 |
| injection | 4 | 1.000 | 1.000 | 1.000 | 0.184 | 1.000 | 1.000 | 0.917 | 0.917 | 0.667 | 1.000 | 17678 |
| simple | 9 | 1.000 | 1.000 | 1.000 | 0.325 | 1.000 | 1.000 | 1.000 | 0.944 | 1.000 | 1.000 | 15849 |
| unanswerable | 6 | 1.000 | 1.000 | – | – | – | – | – | – | – | 1.000 | 17571 |

Refusal precision 0.750, recall 1.000 (8 refused, 6 should be).
Totals: 42 LLM calls, 66822 input / 5228 output tokens, $0.0 generation + $0.012028 judge; 0 answers used the fallback.
