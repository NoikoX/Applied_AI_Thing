# Answers: agent / gemini (42 golden questions)

Models {'planner': 'gemini-3.5-flash-lite', 'answer': 'gemini-3.5-flash-lite', 'grader': 'gemini-3.1-flash-lite', 'judge': 'gpt-5-mini'}, index `golden__large`, commit `1d14df9`.

| slice | n | correct | status_correct | contains | f1 | judge_correct | supported_claims | evidence_recall | citation_precision | citation_recall | llm_calls | latency_ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all | 42 | 0.929 | 0.952 | 0.886 | 0.214 | 0.943 | 1.000 | 0.977 | 0.895 | 0.943 | 5.762 | 79864 |
| bridge | 9 | 0.667 | 0.778 | 0.750 | 0.252 | 0.750 | 1.000 | 0.944 | 0.854 | 0.875 | 5.889 | 2679 |
| comparison | 8 | 1.000 | 1.000 | 0.750 | 0.176 | 1.000 | 1.000 | 1.000 | 0.917 | 1.000 | 5.000 | 19633 |
| contradictory | 6 | 1.000 | 1.000 | 1.000 | 0.095 | 1.000 | 1.000 | 1.000 | 0.778 | 1.000 | 7.000 | 149597 |
| injection | 4 | 1.000 | 1.000 | 1.000 | 0.171 | 1.000 | 1.000 | 0.917 | 1.000 | 0.750 | 6.000 | 128915 |
| simple | 9 | 1.000 | 1.000 | 1.000 | 0.313 | 1.000 | 1.000 | 1.000 | 0.944 | 1.000 | 5.000 | 101370 |
| unanswerable | 6 | 1.000 | 1.000 | – | – | – | – | – | – | – | 6.333 | 141256 |

Refusal precision 0.857, recall 1.000 (7 refused, 6 should be).
Totals: 242 LLM calls, 243344 input / 22855 output tokens, $0.030635 generation + $0.0073 judge; 25 answers used the fallback.
