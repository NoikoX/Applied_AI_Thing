# Retrieval: stages (test split, 500 questions)

Commit `1e04657`, 2026-10-27T19:40:03+00:00. Metrics over the top-K chunks.

Reranker cost: 57.7 ms per scored pair on my laptop CPU. Latency columns include reranker cache hits, so they understate the real cost.

| config | recall@2 | recall@5 | recall@10 | full@2 | full@5 | full@10 | rr | sent_recall@5 | context_words@10 | latency_ms |
|---|---|---|---|---|---|---|---|---|---|---|
| dense | 0.642 | 0.787 | 0.855 | 0.360 | 0.608 | 0.726 | 0.908 | 0.795 | 869 | 237 |
| bm25 | 0.583 | 0.728 | 0.823 | 0.274 | 0.502 | 0.664 | 0.874 | 0.737 | 910 | 19 |
| hybrid-rrf | 0.649 | 0.797 | 0.870 | 0.364 | 0.628 | 0.750 | 0.911 | 0.804 | 888 | 40 |
| hybrid-weighted | 0.674 | 0.822 | 0.878 | 0.410 | 0.668 | 0.762 | 0.923 | 0.829 | 885 | 39 |
| hybrid-rrf+rerank | 0.684 | 0.809 | 0.876 | 0.412 | 0.632 | 0.756 | 0.936 | 0.815 | 865 | 1776 |
| hybrid-rrf+rerank+coverage | 0.684 | 0.809 | 0.876 | 0.412 | 0.632 | 0.756 | 0.936 | 0.815 | 865 | 285 |

By question type (full@5):

| config | bridge | comparison |
|---|---|---|
| dense | 0.532 | 0.946 |
| bm25 | 0.468 | 0.652 |
| hybrid-rrf | 0.578 | 0.848 |
| hybrid-weighted | 0.610 | 0.924 |
| hybrid-rrf+rerank | 0.569 | 0.913 |
| hybrid-rrf+rerank+coverage | 0.569 | 0.913 |
