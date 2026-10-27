import pytest

from investigator.retrieval.fusion import (
    min_max_normalize,
    reciprocal_rank_fusion,
    weighted_fusion,
)


def test_rrf_matches_hand_computation():
    # dense: a, b, c    bm25: c, a, d    (k = 60)
    fused = dict(reciprocal_rank_fusion([["a", "b", "c"], ["c", "a", "d"]], k=60))
    assert fused["a"] == pytest.approx(1 / 61 + 1 / 62)  # 0.032522
    assert fused["c"] == pytest.approx(1 / 63 + 1 / 61)  # 0.032266
    assert fused["b"] == pytest.approx(1 / 62)
    assert fused["d"] == pytest.approx(1 / 63)


def test_rrf_order_rewards_agreement_between_lists():
    ranked = [i for i, _ in reciprocal_rank_fusion([["a", "b", "c"], ["c", "a", "d"]])]
    assert ranked == ["a", "c", "b", "d"]


def test_rrf_ties_keep_first_seen_order():
    ranked = [i for i, _ in reciprocal_rank_fusion([["x", "y"], ["y", "x"]])]
    assert ranked == ["x", "y"]


def test_min_max_normalize():
    assert min_max_normalize({"a": 10, "b": 5, "c": 0}) == {"a": 1.0, "b": 0.5, "c": 0.0}
    assert min_max_normalize({"a": 3, "b": 3}) == {"a": 1.0, "b": 1.0}
    assert min_max_normalize({}) == {}


def test_weighted_fusion_matches_hand_computation():
    dense = {"a": 0.9, "b": 0.5, "c": 0.1}  # normalized: a 1, b 0.5, c 0
    bm25 = {"c": 10.0, "a": 5.0, "d": 0.0}  # normalized: c 1, a 0.5, d 0
    fused = weighted_fusion([dense, bm25], weights=[0.5, 0.5])
    assert fused == [("a", 0.75), ("c", 0.5), ("b", 0.25), ("d", 0.0)]


def test_weighted_fusion_needs_one_weight_per_list():
    with pytest.raises(ValueError):
        weighted_fusion([{"a": 1.0}], weights=[0.5, 0.5])
