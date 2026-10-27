"""Coverage-aware selection: the custom ranking component (hand-written).

Greedy, like MMR (maximal marginal relevance). Each round picks the candidate
with the highest

    relevance  = w_ce * ce + w_rrf * fused_norm
    + w_cov    * [covers a sub-question no selected chunk covers yet]
    - lambda   * max cosine similarity to chunks already selected

skipping documents that already have `max_chunks_per_doc` chunks. It stops at
`final_k` chunks, or early when the best remaining score is below `min_score`.

Why: a multi-hop question needs evidence for each hop. Plain relevance ranking
fills the top K with near-copies of the easiest hop; the redundancy penalty
pushes copies down and the coverage bonus pulls up evidence for the hop that
is still missing.
"""

import math
from dataclasses import dataclass

from investigator.config import CoverageConfig
from investigator.retrieval.candidate import Candidate


@dataclass
class Selection:
    chunks: list[Candidate]
    stopped_early: bool  # True if selection ended because scores fell below min_score


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norms = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norms if norms else 0.0


def relevance(c: Candidate, cfg: CoverageConfig) -> float:
    """Without a reranker the fused score stands in for the cross-encoder score."""
    ce = c.ce if c.ce is not None else c.fused_norm
    return cfg.w_ce * ce + cfg.w_rrf * c.fused_norm


def select_top_k(candidates: list[Candidate], k: int, cfg: CoverageConfig) -> Selection:
    """Baseline: best relevance first, no diversity or coverage."""
    ranked = sorted(candidates, key=lambda c: relevance(c, cfg), reverse=True)[:k]
    for c in ranked:
        c.score = relevance(c, cfg)
        c.components = {"relevance": c.score}
    return Selection(ranked, stopped_early=False)


def select_with_coverage(candidates: list[Candidate], k: int, cfg: CoverageConfig) -> Selection:
    selected: list[Candidate] = []
    covered: set[int] = set()
    per_doc: dict[str, int] = {}
    remaining = list(candidates)

    while remaining and len(selected) < k:
        best, best_score, best_parts = None, -math.inf, {}
        for c in remaining:
            if per_doc.get(c.doc_id, 0) >= cfg.max_chunks_per_doc:
                continue
            parts = {
                "relevance": relevance(c, cfg),
                "coverage": cfg.w_cov if c.covers - covered else 0.0,
                "redundancy": -cfg.redundancy_lambda
                * max((cosine(c.vector, s.vector) for s in selected), default=0.0),
            }
            score = sum(parts.values())
            if score > best_score:  # strict ">" keeps the earlier candidate on ties
                best, best_score, best_parts = c, score, parts
        if best is None:  # every remaining candidate is from a document already at its cap
            break
        if best_score < cfg.min_score:
            return Selection(selected, stopped_early=True)
        best.score, best.components = best_score, best_parts
        selected.append(best)
        remaining.remove(best)
        covered |= best.covers
        per_doc[best.doc_id] = per_doc.get(best.doc_id, 0) + 1

    return Selection(selected, stopped_early=False)
