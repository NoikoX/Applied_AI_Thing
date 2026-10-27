import pytest

from investigator.config import CoverageConfig
from investigator.retrieval.candidate import Candidate
from investigator.retrieval.ranking import cosine, select_top_k, select_with_coverage

CFG = CoverageConfig(
    w_ce=0.6,
    w_rrf=0.4,
    w_cov=0.3,
    redundancy_lambda=0.3,
    max_chunks_per_doc=2,
    covers_top_n=5,
    min_score=0.0,
)


def cand(chunk_id, doc_id, ce, fused_norm, vector, covers=()):
    return Candidate(
        chunk_id, doc_id, title=doc_id, text="", payload={}, fused_norm=fused_norm,
        ce=ce, covers=set(covers), vector=vector,
    )  # fmt: skip


def test_cosine():
    assert cosine([1, 0], [1, 0]) == pytest.approx(1.0)
    assert cosine([1, 0], [0, 1]) == pytest.approx(0.0)
    assert cosine([0, 0], [1, 0]) == 0.0


def test_redundancy_penalty_prefers_a_different_chunk():
    a1 = cand("a1", "A", ce=0.9, fused_norm=1.0, vector=[1, 0])
    a2 = cand("a2", "B", ce=0.88, fused_norm=0.95, vector=[1, 0])  # same content as a1
    b = cand("b", "C", ce=0.8, fused_norm=0.9, vector=[0, 1])
    # Second round: a2 = 0.908 - 0.3 * 1 = 0.608;  b = 0.84 - 0 = 0.84  ->  b wins
    picked = [c.chunk_id for c in select_with_coverage([a1, a2, b], 2, CFG).chunks]
    assert picked == ["a1", "b"]
    # Plain top-k would have taken the near-copy.
    assert [c.chunk_id for c in select_top_k([a1, a2, b], 2, CFG).chunks] == ["a1", "a2"]


def test_coverage_bonus_brings_in_the_missing_hop():
    hop1 = cand("h1", "A", ce=0.9, fused_norm=1.0, vector=[1, 0, 0], covers={1})
    hop1_more = cand("h1b", "B", ce=0.8, fused_norm=0.9, vector=[0, 1, 0], covers={1})
    hop2 = cand("h2", "C", ce=0.6, fused_norm=0.7, vector=[0, 0, 1], covers={2})
    # Second round: h1b = 0.84 (sub-question 1 already covered);  h2 = 0.64 + 0.3 = 0.94
    picked = [c.chunk_id for c in select_with_coverage([hop1, hop1_more, hop2], 2, CFG).chunks]
    assert picked == ["h1", "h2"]


def test_max_chunks_per_document():
    same_doc = [cand(f"c{i}", "A", ce=0.9, fused_norm=1.0, vector=[1, i]) for i in range(4)]
    # Relevance 0.5, minus 0.3 * cos([0, 1], [1, 1]) = 0.21 -> 0.29, still above min_score.
    other = cand("o", "B", ce=0.5, fused_norm=0.5, vector=[0, 1])
    picked = select_with_coverage([*same_doc, other], 4, CFG).chunks
    assert [c.doc_id for c in picked] == ["A", "A", "B"]


def test_stops_early_below_min_score():
    good = cand("g", "A", ce=0.9, fused_norm=1.0, vector=[1, 0])
    copy = cand("c", "B", ce=0.1, fused_norm=0.1, vector=[1, 0])  # 0.1 - 0.3 = -0.2
    selection = select_with_coverage([good, copy], 5, CFG)
    assert [c.chunk_id for c in selection.chunks] == ["g"]
    assert selection.stopped_early is True


def test_score_breakdown_is_recorded():
    c = cand("x", "A", ce=0.5, fused_norm=1.0, vector=[1, 0], covers={1})
    chosen = select_with_coverage([c], 1, CFG).chunks[0]
    assert chosen.components == pytest.approx(
        {"relevance": 0.7, "coverage": 0.3, "redundancy": 0.0}
    )
    assert chosen.score == pytest.approx(1.0)


def test_without_reranker_fused_score_stands_in():
    c = cand("x", "A", ce=None, fused_norm=0.5, vector=[1, 0])
    assert select_top_k([c], 1, CFG).chunks[0].score == pytest.approx(0.5)
