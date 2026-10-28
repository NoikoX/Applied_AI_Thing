from investigator.ingestion.dedup import content_hash, fact_tokens, normalize_text, same_facts


def test_fact_tokens_are_numbers_and_names():
    assert fact_tokens("On 12 March the Payment queue slowed, v2.1 rolled back.") == {
        "12", "march", "payment", "on", "v2",  "1",
    }  # fmt: skip


def test_same_facts_ignores_wording_but_not_values():
    a = "The outage began on 12 March after change CH-42."
    assert same_facts(a, "The outage began on 12 March after change CH-42 today.")
    assert not same_facts(a, "The outage began on 14 March after change CH-42.")
    assert not same_facts(a, "The outage began on 12 March after change CH-43.")


def test_normalize_collapses_whitespace_and_case():
    assert normalize_text("  Hello\n\tWORLD  ") == "hello world"


def test_trivial_variants_hash_equal():
    assert content_hash("Paris", "Capital of France.") == content_hash(
        "paris", "  Capital  of\nFrance. "
    )


def test_title_is_part_of_the_hash():
    assert content_hash("A", "same text") != content_hash("B", "same text")
