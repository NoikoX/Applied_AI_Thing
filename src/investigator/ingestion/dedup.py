"""Duplicate detection: exact (hash of normalized text) and the near-duplicate fact check."""

import hashlib
import re
import unicodedata


def normalize_text(text: str) -> str:
    """Unicode-normalize, lower-case and collapse whitespace, so trivial variants hash equal."""
    return " ".join(unicodedata.normalize("NFC", text).lower().split())


def content_hash(title: str, text: str) -> str:
    """SHA-256 of the normalized title and text."""
    key = normalize_text(title) + "\n" + normalize_text(text)
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def fact_tokens(text: str) -> set[str]:
    """Words that carry checkable facts: anything with a digit (years, amounts, versions)
    and capitalized words (names of people, places, products)."""
    words = re.findall(r"\w+", unicodedata.normalize("NFC", text))
    return {w.lower() for w in words if any(ch.isdigit() for ch in w) or w[0].isupper()}


def same_facts(a: str, b: str) -> bool:
    """True if two similar texts state the same numbers and names.

    Embedding similarity barely moves when one date changes ("12 March" vs
    "14 March"), so cosine alone would call a disagreeing source a duplicate.
    """
    return fact_tokens(a) == fact_tokens(b)
