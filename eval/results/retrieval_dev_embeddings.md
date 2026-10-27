# Retrieval: embeddings (dev split, 200 questions)

Commit `1e04657`, 2026-10-27T19:50:00+00:00. Metrics over the top-K chunks.

Reranker cost: 0.0 ms per scored pair on my laptop CPU. Latency columns include reranker cache hits, so they understate the real cost.

| config | recall@2 | recall@5 | recall@10 | full@2 | full@5 | full@10 | rr | sent_recall@5 | context_words@10 | latency_ms |
|---|---|---|---|---|---|---|---|---|---|---|
| small-dense | 0.645 | 0.795 | 0.835 | 0.330 | 0.605 | 0.670 | 0.922 | 0.803 | 866 | 229 |
| large-dense | 0.705 | 0.835 | 0.895 | 0.455 | 0.690 | 0.790 | 0.938 | 0.842 | 866 | 262 |
| small-hybrid-rrf | 0.640 | 0.805 | 0.887 | 0.340 | 0.620 | 0.775 | 0.918 | 0.809 | 895 | 35 |
| large-hybrid-rrf | 0.682 | 0.850 | 0.900 | 0.395 | 0.705 | 0.800 | 0.948 | 0.853 | 882 | 39 |
| small-hybrid-weighted | 0.680 | 0.833 | 0.877 | 0.405 | 0.665 | 0.755 | 0.934 | 0.838 | 898 | 36 |
| large-hybrid-weighted | 0.705 | 0.860 | 0.910 | 0.430 | 0.720 | 0.820 | 0.962 | 0.866 | 893 | 36 |

By question type (full@5):

| config | bridge | comparison |
|---|---|---|
| small-dense | 0.522 | 0.927 |
| large-dense | 0.616 | 0.976 |
| small-hybrid-rrf | 0.566 | 0.829 |
| large-hybrid-rrf | 0.654 | 0.902 |
| small-hybrid-weighted | 0.604 | 0.902 |
| large-hybrid-weighted | 0.667 | 0.927 |
