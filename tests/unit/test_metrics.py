import pytest

from investigator.evaluation.metrics import (
    RetrievedChunk,
    full_support_at_k,
    mean,
    recall_at_k,
    reciprocal_rank,
    sentence_recall_at_k,
)

GOLD = ["A", "B"]
# Ranking: X, A, A, Y, B
RANKING = [RetrievedChunk(d) for d in ["X", "A", "A", "Y", "B"]]


@pytest.mark.parametrize("k, expected", [(1, 0.0), (2, 0.5), (4, 0.5), (5, 1.0), (50, 1.0)])
def test_recall_at_k(k, expected):
    assert recall_at_k(RANKING, GOLD, k) == expected


def test_duplicate_chunks_of_one_doc_count_once():
    assert recall_at_k([RetrievedChunk("A")] * 3, GOLD, 3) == 0.5


def test_full_support_needs_every_gold_doc():
    assert full_support_at_k(RANKING, GOLD, 4) is False
    assert full_support_at_k(RANKING, GOLD, 5) is True


def test_reciprocal_rank():
    assert reciprocal_rank(RANKING, GOLD) == 0.5  # first gold chunk at position 2
    assert reciprocal_rank([RetrievedChunk("B")], GOLD) == 1.0
    assert reciprocal_rank([RetrievedChunk("X")], GOLD) == 0.0


def test_sentence_recall_with_windows():
    facts = [("A", 0), ("A", 4), ("B", 1)]
    windows = [RetrievedChunk("A", 0, 3), RetrievedChunk("B", 2, 5), RetrievedChunk("A", 3, 6)]
    assert sentence_recall_at_k(windows, facts, 1) == pytest.approx(1 / 3)  # only A:0
    assert sentence_recall_at_k(windows, facts, 3) == pytest.approx(2 / 3)  # B:1 never covered


def test_paragraph_chunk_covers_all_its_sentences():
    facts = [("A", 0), ("A", 7)]
    assert sentence_recall_at_k([RetrievedChunk("A")], facts, 1) == 1.0


def test_sentence_recall_without_labels_is_none():
    assert sentence_recall_at_k(RANKING, [], 5) is None


def test_mean_skips_none_and_counts_booleans():
    assert mean([1.0, None, 0.0]) == 0.5
    assert mean([True, False, True, True]) == 0.75
    assert mean([None]) is None
