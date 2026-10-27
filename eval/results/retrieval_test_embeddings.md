# Retrieval: embeddings (test split, 500 questions)

Commit `1e04657`, 2026-10-27T19:55:12+00:00. Metrics over the top-K chunks.

Reranker cost: 0.0 ms per scored pair on my laptop CPU. Latency columns include reranker cache hits, so they understate the real cost.

| config | recall@2 | recall@5 | recall@10 | full@2 | full@5 | full@10 | rr | sent_recall@5 | context_words@10 | latency_ms |
|---|---|---|---|---|---|---|---|---|---|---|
| small-dense | 0.642 | 0.787 | 0.855 | 0.360 | 0.608 | 0.726 | 0.908 | 0.795 | 869 | 221 |
| large-dense | 0.702 | 0.853 | 0.903 | 0.460 | 0.722 | 0.814 | 0.925 | 0.858 | 858 | 248 |
| small-hybrid-rrf | 0.649 | 0.797 | 0.870 | 0.364 | 0.628 | 0.750 | 0.911 | 0.804 | 888 | 35 |
| large-hybrid-rrf | 0.676 | 0.831 | 0.899 | 0.406 | 0.684 | 0.806 | 0.924 | 0.837 | 885 | 36 |
| small-hybrid-weighted | 0.674 | 0.822 | 0.878 | 0.410 | 0.668 | 0.762 | 0.923 | 0.829 | 885 | 36 |
| large-hybrid-weighted | 0.709 | 0.845 | 0.915 | 0.460 | 0.712 | 0.834 | 0.942 | 0.849 | 876 | 38 |

By question type (full@5):

| config | bridge | comparison |
|---|---|---|
| small-dense | 0.532 | 0.946 |
| large-dense | 0.667 | 0.967 |
| small-hybrid-rrf | 0.578 | 0.848 |
| large-hybrid-rrf | 0.640 | 0.880 |
| small-hybrid-weighted | 0.610 | 0.924 |
| large-hybrid-weighted | 0.669 | 0.902 |
