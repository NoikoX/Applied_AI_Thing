# Retrieval: tuning (dev split, 200 questions)

Commit `1e04657`, 2026-10-27T19:19:42+00:00. Metrics over the top-K chunks.

Reranker cost: 68.4 ms per scored pair on my laptop CPU. Latency columns include reranker cache hits, so they understate the real cost.

| config | recall@2 | recall@5 | recall@10 | full@2 | full@5 | full@10 | rr | sent_recall@5 | context_words@10 | latency_ms |
|---|---|---|---|---|---|---|---|---|---|---|
| weighted-a0.3 | 0.637 | 0.807 | 0.870 | 0.335 | 0.620 | 0.745 | 0.923 | 0.811 | 923 | 247 |
| weighted-a0.5 | 0.680 | 0.833 | 0.877 | 0.405 | 0.665 | 0.755 | 0.934 | 0.838 | 898 | 33 |
| weighted-a0.7 | 0.680 | 0.823 | 0.875 | 0.385 | 0.645 | 0.750 | 0.937 | 0.828 | 878 | 35 |
| weighted-a0.9 | 0.655 | 0.805 | 0.845 | 0.345 | 0.620 | 0.690 | 0.928 | 0.812 | 866 | 34 |
| coverage-l0.0 | 0.682 | 0.825 | 0.887 | 0.390 | 0.650 | 0.775 | 0.973 | 0.832 | 867 | 2667 |
| coverage-l0.15 | 0.700 | 0.823 | 0.880 | 0.420 | 0.650 | 0.760 | 0.973 | 0.827 | 881 | 318 |
| coverage-l0.3 | 0.695 | 0.812 | 0.870 | 0.415 | 0.630 | 0.740 | 0.971 | 0.819 | 891 | 309 |

By question type (full@5):

| config | bridge | comparison |
|---|---|---|
| weighted-a0.3 | 0.572 | 0.805 |
| weighted-a0.5 | 0.604 | 0.902 |
| weighted-a0.7 | 0.566 | 0.951 |
| weighted-a0.9 | 0.535 | 0.951 |
| coverage-l0.0 | 0.585 | 0.902 |
| coverage-l0.15 | 0.579 | 0.927 |
| coverage-l0.3 | 0.553 | 0.927 |
