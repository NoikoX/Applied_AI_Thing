import pytest

from investigator.evaluation.golden import (
    INJECTION_MARKER,
    altered_value,
    contradicting_text,
    docs_mentioning,
    injected_text,
    mentions,
    sentence_with,
)


def test_mentions_whole_phrase_only():
    assert mentions("Founded in 1945 in Milan.", "1945")
    assert not mentions("Code 19450.", "1945")
    assert mentions("The WIRE aired on HBO", "the wire")


def test_mentions_ignores_punctuation():
    # Regression (M11, G20): the hyphenated spelling hid a second source.
    assert mentions('known as the "Not Ready for Prime-Time Players"', "Prime Time Players")
    assert mentions("based in Washington, D.C.", "Washington D.C")
    assert not mentions("anything", "")


def test_docs_mentioning_checks_title_and_text():
    docs = {"a": {"title": "Milan", "text": "A city."}, "b": {"title": "X", "text": "near milan"}}
    assert docs_mentioning("Milan", docs) == ["a", "b"]


@pytest.mark.parametrize(
    "answer, changed",
    [("1945", "1952"), ("2018", "2025"), ("12", "27"), ("1,200", "2,403"), ("Milan", None)],
)
def test_altered_value(answer, changed):
    assert altered_value(answer) == changed


def test_sentence_with():
    text = "Techint is a conglomerate. It was founded in Milan in 1945. It has offices."
    assert sentence_with(text, "1945") == "It was founded in Milan in 1945."
    assert sentence_with(text, "Paris") is None


def test_contradicting_text_changes_only_the_value_and_names_the_subject():
    text = contradicting_text("Techint", "Techint was founded in Milan in 1945.", "1945", "1952")
    assert "1952" in text and "1945" not in text
    assert text.startswith("Archive record: Techint")


def test_contradicting_text_needs_the_answer_in_the_paragraph():
    assert contradicting_text("T", "No year here.", "1945", "1952") is None


def test_injected_text_keeps_the_facts():
    text = injected_text("Techint", "Founded in Milan.")
    assert "Founded in Milan." in text and INJECTION_MARKER in text
