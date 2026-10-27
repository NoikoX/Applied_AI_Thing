"""Exact-duplicate detection by hashing normalized text."""

import hashlib
import unicodedata


def normalize_text(text: str) -> str:
    """Unicode-normalize, lower-case and collapse whitespace, so trivial variants hash equal."""
    return " ".join(unicodedata.normalize("NFC", text).lower().split())


def content_hash(title: str, text: str) -> str:
    """SHA-256 of the normalized title and text."""
    key = normalize_text(title) + "\n" + normalize_text(text)
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
