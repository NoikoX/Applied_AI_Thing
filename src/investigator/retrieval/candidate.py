"""A retrieved chunk moving through fusion, reranking and selection."""

from dataclasses import dataclass, field


@dataclass
class Candidate:
    chunk_id: str
    doc_id: str
    title: str
    text: str
    payload: dict
    fused: float = 0.0  # best fusion score over the main query and sub-queries
    fused_norm: float = 0.0  # fused / best fused in the pool, 0..1
    ce: float | None = None  # cross-encoder relevance to the main query, 0..1
    covers: set[int] = field(default_factory=set)  # sub-query numbers it ranks high for (1-based)
    vector: list[float] | None = None  # dense vector, fetched for the redundancy penalty
    score: float = 0.0  # final score when it was selected
    components: dict = field(default_factory=dict)  # breakdown of `score`, for debugging and UI
