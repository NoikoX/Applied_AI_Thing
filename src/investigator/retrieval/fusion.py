"""Combining ranked lists from dense and keyword search (hand-written).

Both functions return [(id, score), ...] sorted best first. Ties keep the
order in which ids were first seen, so results are deterministic.
"""


def _sorted(scores: dict[str, float]) -> list[tuple[str, float]]:
    # dicts keep insertion order and sorted() is stable, so ties stay in first-seen order.
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


def reciprocal_rank_fusion(ranked_lists: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """RRF: score(id) = sum over lists of 1 / (k + rank), rank starting at 1.

    Uses only positions, never raw scores, so a cosine similarity (0..1) and a
    BM25 score (0..30+) can be combined without calibrating them. A larger k
    flattens the difference between rank 1 and rank 10.
    """
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, item_id in enumerate(ranked, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return _sorted(scores)


def min_max_normalize(scores: dict[str, float]) -> dict[str, float]:
    """Scale to 0..1 within one list. If all scores are equal they all become 1."""
    if not scores:
        return {}
    low, high = min(scores.values()), max(scores.values())
    if high == low:
        return dict.fromkeys(scores, 1.0)
    return {i: (s - low) / (high - low) for i, s in scores.items()}


def weighted_fusion(
    score_lists: list[dict[str, float]], weights: list[float]
) -> list[tuple[str, float]]:
    """Weighted sum of min-max normalized scores.

    An id missing from a list counts as 0 there (it ranked below that list's cut-off).
    Unlike RRF, the size of score gaps matters, not just the order.
    """
    if len(score_lists) != len(weights):
        raise ValueError("Need one weight per list")
    scores: dict[str, float] = {}
    for raw, weight in zip(score_lists, weights, strict=True):
        for item_id, s in min_max_normalize(raw).items():
            scores[item_id] = scores.get(item_id, 0.0) + weight * s
    return _sorted(scores)
