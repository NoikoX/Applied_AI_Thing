from investigator.ingestion.dedup import content_hash, normalize_text


def test_normalize_collapses_whitespace_and_case():
    assert normalize_text("  Hello\n\tWORLD  ") == "hello world"


def test_trivial_variants_hash_equal():
    assert content_hash("Paris", "Capital of France.") == content_hash(
        "paris", "  Capital  of\nFrance. "
    )


def test_title_is_part_of_the_hash():
    assert content_hash("A", "same text") != content_hash("B", "same text")
