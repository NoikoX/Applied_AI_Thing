import pytest

from investigator.evaluation.answer_metrics import (
    citation_precision,
    citation_recall,
    contains_answer,
    exact_match,
    normalize_answer,
    refusal_scores,
    token_f1,
)


def test_normalize_answer():
    assert normalize_answer("The  Wire!") == "wire"
    assert normalize_answer("Washington, D.C.") == "washington dc"


def test_exact_match():
    assert exact_match("the Western Conference.", "Western Conference")
    assert not exact_match("John Doman acted in it", "John Doman")


def test_token_f1_matches_hand_computation():
    # pred: john doman acted in both   gold: john doman   common 2 -> P 2/5, R 1 -> F1 4/7
    assert token_f1("John Doman acted in both", "John Doman") == pytest.approx(4 / 7)
    assert token_f1("Paris", "London") == 0.0
    assert token_f1("", "") == 1.0


def test_contains_answer_whole_words():
    assert contains_answer("It was founded in Milan, Italy.", "Milan")
    assert not contains_answer("Founded in 19450", "1945")
    assert not contains_answer("anything", "")


def test_citation_precision_and_recall():
    assert citation_precision(["a", "x"], ["a", "b"]) == 0.5
    assert citation_recall(["a", "x"], ["a", "b"]) == 0.5
    assert citation_precision([], ["a"]) is None
    assert citation_recall(["a"], []) is None
    assert citation_precision(["a", "a"], ["a"]) == 1.0


def test_refusal_scores():
    rows = [
        {"status": "insufficient_evidence", "expected_status": "insufficient_evidence"},
        {"status": "insufficient_evidence", "expected_status": "answered"},  # wrong refusal
        {"status": "answered", "expected_status": "insufficient_evidence"},  # missed refusal
        {"status": "answered", "expected_status": "answered"},
    ]
    s = refusal_scores(rows)
    assert (s["refusal_precision"], s["refusal_recall"]) == (0.5, 0.5)
    assert (
        refusal_scores([{"status": "answered", "expected_status": "answered"}])["refusal_precision"]
        is None
    )
