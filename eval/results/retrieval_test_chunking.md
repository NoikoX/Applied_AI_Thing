# Retrieval: chunking (test split, 500 questions)

Commit `1e04657`, 2026-10-27T19:47:13+00:00. Metrics over the top-K chunks.

Reranker cost: 24.8 ms per scored pair on my laptop CPU. Latency columns include reranker cache hits, so they understate the real cost.

| config | recall@2 | recall@5 | recall@10 | full@2 | full@5 | full@10 | rr | sent_recall@5 | context_words@10 | latency_ms |
|---|---|---|---|---|---|---|---|---|---|---|
| A-dense | 0.642 | 0.787 | 0.855 | 0.360 | 0.608 | 0.726 | 0.908 | 0.795 | 869 | 225 |
| B-dense | 0.598 | 0.749 | 0.825 | 0.282 | 0.544 | 0.678 | 0.900 | 0.747 | 600 | 28 |
| A-hybrid-rrf+rerank | 0.684 | 0.809 | 0.876 | 0.412 | 0.632 | 0.756 | 0.936 | 0.815 | 865 | 37 |
| B-hybrid-rrf+rerank | 0.644 | 0.787 | 0.860 | 0.338 | 0.598 | 0.728 | 0.937 | 0.786 | 598 | 558 |

By question type (full@5):

| config | bridge | comparison |
|---|---|---|
| A-dense | 0.532 | 0.946 |
| B-dense | 0.468 | 0.880 |
| A-hybrid-rrf+rerank | 0.569 | 0.913 |
| B-hybrid-rrf+rerank | 0.534 | 0.880 |
