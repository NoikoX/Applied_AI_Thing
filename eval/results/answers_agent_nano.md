# Answers: agent / nano (42 golden questions)

Models {'planner': 'gpt-5-nano', 'answer': 'gpt-5-nano', 'grader': 'gpt-5-nano', 'judge': 'gpt-5-mini'}, index `golden__large`, commit `8266f1d`.

| slice | n | correct | status_correct | contains | f1 | judge_correct | supported_claims | evidence_recall | citation_precision | citation_recall | llm_calls | latency_ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all | 42 | 0.548 | 0.619 | 0.762 | 0.670 | 0.809 | 0.976 | 0.917 | 0.929 | 0.818 | 5.381 | 2704 |
| bridge | 9 | 0.444 | 0.556 | 0.600 | 0.692 | 0.800 | 0.900 | 0.889 | 1.000 | 0.700 | 5.000 | 2341 |
| comparison | 8 | 0.375 | 0.500 | 0.750 | 0.524 | 0.750 | 1.000 | 1.000 | 1.000 | 1.000 | 5.750 | 2963 |
| contradictory | 6 | 0.167 | 0.167 | 0.500 | 0.500 | 0.500 | 1.000 | 0.667 | 0.500 | 0.500 | 5.000 | 1994 |
| injection | 4 | 0.250 | 0.500 | 0.500 | 0.053 | 0.500 | 1.000 | 1.000 | 1.000 | 0.333 | 5.500 | 2666 |
| simple | 9 | 0.889 | 0.889 | 1.000 | 0.925 | 1.000 | 1.000 | 1.000 | 0.938 | 1.000 | 5.000 | 2200 |
| unanswerable | 6 | 1.000 | 1.000 | – | – | – | – | – | – | – | 6.333 | 4392 |

Refusal precision 0.286, recall 1.000 (21 refused, 6 should be).
Totals: 226 LLM calls, 249576 input / 15407 output tokens, $0.0 generation + $0.0 judge; 0 answers used the fallback.
