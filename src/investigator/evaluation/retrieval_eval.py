"""Run retrieval configurations over gold questions and aggregate the metrics."""

import hashlib
import sqlite3
import time
from pathlib import Path

from investigator.config import RetrievalConfig, with_overrides
from investigator.evaluation.metrics import (
    RetrievedChunk,
    full_support_at_k,
    mean,
    recall_at_k,
    reciprocal_rank,
    sentence_recall_at_k,
)
from investigator.retrieval.search import HybridRetriever

RECALL_KS = (1, 2, 5, 10)
FULL_KS = (2, 5, 10)
SENTENCE_KS = (5, 10)


def apply_overrides(base: RetrievalConfig, overrides: dict) -> RetrievalConfig:
    """Config with some settings replaced; nested sections merge, unknown keys raise."""
    return with_overrides(base, overrides)


class CachedQueryEmbedder:
    """Wraps an embedder so each question is embedded once, however many configs reuse it."""

    def __init__(self, inner):
        self.inner = inner
        self.model = inner.model
        self.dimensions = inner.dimensions
        self._cache: dict[str, list[float]] = {}

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.inner.embed(texts)

    def embed_queries(self, queries: list[str]) -> list[list[float]]:
        missing = [q for q in dict.fromkeys(queries) if q not in self._cache]
        if missing:
            self._cache.update(zip(missing, self.inner.embed_queries(missing), strict=True))
        return [self._cache[q] for q in queries]


class CachedReranker:
    """Keeps cross-encoder scores in a SQLite file, keyed by (model, query, passage).

    Configs that rerank the same candidates (e.g. "+rerank" and "+rerank+coverage")
    and later runs then score each pair only once. Scores are identical either way;
    only wall-clock time changes, so the true cost is tracked separately (ms per
    scored pair) instead of being read from the cached runs' latency.
    """

    def __init__(self, inner, model_name: str, path: Path):
        self.inner = inner
        self.model_name = model_name
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path)
        self._db.execute("CREATE TABLE IF NOT EXISTS scores (key TEXT PRIMARY KEY, score REAL)")
        self.hits = 0
        self.misses = 0
        self.scoring_ms = 0.0  # time spent in the real model

    def _key(self, query: str, text: str) -> str:
        return hashlib.sha256(f"{self.model_name}\0{query}\0{text}".encode()).hexdigest()

    def score(self, query: str, texts: list[str]) -> list[float]:
        keys = [self._key(query, t) for t in texts]
        placeholders = ",".join("?" * len(keys))
        found = dict(
            self._db.execute(f"SELECT key, score FROM scores WHERE key IN ({placeholders})", keys)
        )
        missing = [i for i, k in enumerate(keys) if k not in found]
        if missing:
            start = time.perf_counter()
            new = self.inner.score(query, [texts[i] for i in missing])
            self.scoring_ms += (time.perf_counter() - start) * 1000
            rows = [(keys[i], s) for i, s in zip(missing, new, strict=True)]
            self._db.executemany("INSERT OR REPLACE INTO scores VALUES (?, ?)", rows)
            self._db.commit()
            found.update(rows)
        self.hits += len(keys) - len(missing)
        self.misses += len(missing)
        return [found[k] for k in keys]

    def ms_per_pair(self) -> float | None:
        return self.scoring_ms / self.misses if self.misses else None


def evaluate_question(retriever: HybridRetriever, question: dict) -> dict:
    start = time.perf_counter()
    result = retriever.search(question["question"])
    latency_ms = (time.perf_counter() - start) * 1000

    chunks = [
        RetrievedChunk(c.doc_id, c.payload.get("sent_start"), c.payload.get("sent_end"))
        for c in result.chunks
    ]
    gold = question["gold_doc_ids"]
    facts = [(f["doc_id"], f["sent_id"]) for f in question["supporting_facts"]]
    row = {"id": question["id"], "type": question["type"], "rr": reciprocal_rank(chunks, gold)}
    row |= {f"recall@{k}": recall_at_k(chunks, gold, k) for k in RECALL_KS}
    row |= {f"full@{k}": full_support_at_k(chunks, gold, k) for k in FULL_KS}
    row |= {f"sent_recall@{k}": sentence_recall_at_k(chunks, facts, k) for k in SENTENCE_KS}
    row["context_words@10"] = sum(len(c.text.split()) for c in result.chunks[:10])
    row["latency_ms"] = round(latency_ms, 1)
    row["rerank_ms"] = result.timings_ms.get("rerank", 0.0)
    row["top_titles"] = [c.title for c in result.chunks[:5]]  # for failure analysis
    return row


def summarize(rows: list[dict]) -> dict:
    """Mean of every numeric metric, overall and per question type (bridge / comparison)."""
    metric_names = [k for k, v in rows[0].items() if isinstance(v, (int, float, bool, type(None)))]

    def means(subset: list[dict]) -> dict:
        out = {"n": len(subset)}
        for name in metric_names:
            value = mean([r[name] for r in subset])
            out[name] = round(value, 4) if value is not None else None
        return out

    summary = {"all": means(rows)}
    for qtype in sorted({r["type"] for r in rows}):
        summary[qtype] = means([r for r in rows if r["type"] == qtype])
    return summary
