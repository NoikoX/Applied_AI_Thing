# Answers: baseline / mini (42 golden questions)

Models {'planner': 'gpt-5-mini', 'answer': 'gpt-5-mini', 'grader': 'gpt-5-mini', 'judge': 'gpt-5-mini'}, index `golden__large`, commit `8266f1d`.

| slice | n | correct | status_correct | contains | f1 | judge_correct | supported_claims | evidence_recall | citation_precision | citation_recall | llm_calls | latency_ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all | 42 | 0.786 | 0.857 | 0.829 | 0.430 | 0.886 | 0.974 | 0.931 | 0.769 | 0.895 | 0.952 | 2135 |
| bridge | 9 | 0.778 | 1.000 | 0.667 | 0.457 | 0.778 | 0.944 | 0.889 | 0.852 | 0.833 | 1.000 | 2183 |
| comparison | 8 | 0.875 | 1.000 | 0.750 | 0.458 | 0.875 | 1.000 | 1.000 | 0.925 | 1.000 | 1.000 | 2149 |
| contradictory | 6 | 0.500 | 0.500 | 0.800 | 0.189 | 0.800 | 1.000 | 0.750 | 0.500 | 0.700 | 1.000 | 1892 |
| injection | 4 | 1.000 | 1.000 | 1.000 | 0.568 | 1.000 | 1.000 | 1.000 | 0.917 | 0.833 | 1.000 | 2939 |
| simple | 9 | 1.000 | 1.000 | 1.000 | 0.451 | 1.000 | 1.000 | 1.000 | 0.889 | 1.000 | 1.000 | 1818 |
| unanswerable | 6 | 0.500 | 0.500 | – | – | – | 0.833 | – | 0.000 | – | 0.667 | 2226 |

Refusal precision 0.750, recall 0.500 (4 refused, 6 should be).
Totals: 40 LLM calls, 69856 input / 4225 output tokens, $0.000633 generation + $0.000817 judge; 0 answers used the fallback.
