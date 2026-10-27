"""Hybrid retrieval pipeline.

  1. For the question and each sub-question: dense search + BM25 search, fused (RRF or weighted).
  2. Pool the candidates; each keeps its best fused score and the sub-questions it covers.
  3. Rerank the top `rerank_top_n` with the cross-encoder against the main question.
  4. Select `final_k` chunks: plain top-k, or coverage-aware selection.

Every stage can be switched off in config, which is how the evaluation
compares dense vs BM25 vs hybrid, with and without reranking and coverage.
"""

import time
from dataclasses import dataclass, field

from qdrant_client import QdrantClient

from investigator.config import RetrievalConfig
from investigator.index.embeddings import DenseEmbedder
from investigator.index.qdrant_store import DENSE, SPARSE, chunks_collection
from investigator.index.sparse import SparseEncoder
from investigator.retrieval.candidate import Candidate
from investigator.retrieval.fusion import reciprocal_rank_fusion, weighted_fusion
from investigator.retrieval.ranking import select_top_k, select_with_coverage
from investigator.retrieval.rerank import Reranker


@dataclass
class RetrievalResult:
    chunks: list[Candidate]
    stopped_early: bool
    n_candidates: int
    timings_ms: dict[str, float] = field(default_factory=dict)


class HybridRetriever:
    def __init__(
        self,
        client: QdrantClient,
        strategy: str,
        cfg: RetrievalConfig,
        dense: DenseEmbedder,
        sparse: SparseEncoder,
        reranker: Reranker | None,
    ):
        if cfg.rerank and reranker is None:
            raise ValueError("Config enables reranking but no reranker was given")
        self.client = client
        self.collection = chunks_collection(strategy)
        self.cfg = cfg
        self.dense = dense
        self.sparse = sparse
        self.reranker = reranker

    def search(self, query: str, subqueries: list[str] | None = None) -> RetrievalResult:
        cfg = self.cfg
        timings: dict[str, float] = {}
        clock = time.perf_counter()

        def lap(name: str) -> None:
            nonlocal clock
            now = time.perf_counter()
            timings[name] = round((now - clock) * 1000, 1)
            clock = now

        queries = [query, *(subqueries or [])]
        vectors = self.dense.embed(queries) if cfg.mode != "sparse" else [None] * len(queries)
        lap("embed")

        pool: dict[str, Candidate] = {}
        for q_num, (q, vector) in enumerate(zip(queries, vectors, strict=True)):
            for rank, (chunk_id, fused, payload) in enumerate(self._search_one(q, vector)):
                c = pool.get(chunk_id)
                if c is None:
                    c = pool[chunk_id] = Candidate(
                        chunk_id, payload["doc_id"], payload["title"], payload["text"], payload
                    )
                c.fused = max(c.fused, fused)
                if q_num > 0 and rank < cfg.coverage.covers_top_n:
                    c.covers.add(q_num)
        lap("search")

        candidates = sorted(pool.values(), key=lambda c: c.fused, reverse=True)
        candidates = candidates[: cfg.rerank_top_n]
        best = candidates[0].fused if candidates else 1.0
        for c in candidates:
            c.fused_norm = c.fused / best

        if cfg.rerank and candidates:
            texts = [f"{c.title}\n{c.text}" for c in candidates]  # same format as indexing
            for c, s in zip(candidates, self.reranker.score(query, texts), strict=True):
                c.ce = s
        lap("rerank")

        if cfg.selection == "coverage":
            self._attach_vectors(candidates)
            selection = select_with_coverage(candidates, cfg.final_k, cfg.coverage)
        else:
            selection = select_top_k(candidates, cfg.final_k, cfg.coverage)
        lap("select")

        return RetrievalResult(selection.chunks, selection.stopped_early, len(pool), timings)

    def _search_one(self, query: str, vector: list[float] | None):
        """Fused hits for one query: [(chunk_id, fused score, payload), ...], best first."""
        n = self.cfg.candidates_per_list
        lists = []
        if self.cfg.mode in ("dense", "hybrid"):
            lists.append(self._query(vector, DENSE, n))
        if self.cfg.mode in ("sparse", "hybrid"):
            lists.append(self._query(self.sparse.embed_query(query), SPARSE, n))

        payloads = {str(p.id): p.payload for hits in lists for p in hits}
        if self.cfg.fusion == "rrf":
            fused = reciprocal_rank_fusion(
                [[str(p.id) for p in hits] for hits in lists], self.cfg.rrf_k
            )
        else:
            weights = (
                [self.cfg.dense_weight, 1 - self.cfg.dense_weight] if len(lists) == 2 else [1.0]
            )
            fused = weighted_fusion([{str(p.id): p.score for p in hits} for hits in lists], weights)
        return [(chunk_id, score, payloads[chunk_id]) for chunk_id, score in fused[:n]]

    def _query(self, query, using: str, limit: int):
        return self.client.query_points(
            self.collection, query=query, using=using, limit=limit, with_payload=True
        ).points

    def _attach_vectors(self, candidates: list[Candidate]) -> None:
        """Fetch dense vectors for the redundancy penalty (BM25-only hits arrive without one)."""
        points = self.client.retrieve(
            self.collection, [c.chunk_id for c in candidates], with_vectors=[DENSE]
        )
        by_id = {str(p.id): p.vector[DENSE] for p in points}
        for c in candidates:
            c.vector = by_id[c.chunk_id]
