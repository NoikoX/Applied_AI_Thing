"""Offline stand-ins for the OpenAI embedder and the BM25 encoder."""

import hashlib
import math
import re

from qdrant_client import models


def _tokens(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _bucket(token: str, n: int) -> int:
    return int(hashlib.md5(token.encode()).hexdigest(), 16) % n


class HashEmbedder:
    """Bag-of-words hashed into a small vector and L2-normalized.

    Texts that share most words get a cosine similarity close to 1, which is
    enough to test near-duplicate detection without calling an API.
    """

    model = "fake-hash"

    def __init__(self, dimensions: int = 256):
        self.dimensions = dimensions
        self.calls: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        vectors = []
        for text in texts:
            v = [0.0] * self.dimensions
            for t in _tokens(text):
                v[_bucket(t, self.dimensions)] += 1.0
            norm = math.sqrt(sum(x * x for x in v)) or 1.0
            vectors.append([x / norm for x in v])
        return vectors


class FakeReranker:
    """Relevance = share of query words that appear in the text."""

    def score(self, query: str, texts: list[str]) -> list[float]:
        q = set(_tokens(query))
        return [len(q & set(_tokens(t))) / len(q) if q else 0.0 for t in texts]


class FakeSparse:
    """Term counts keyed by hashed token IDs."""

    def _vector(self, text: str) -> models.SparseVector:
        counts: dict[int, float] = {}
        for t in _tokens(text):
            i = _bucket(t, 100_000)
            counts[i] = counts.get(i, 0.0) + 1.0
        indices = sorted(counts)
        return models.SparseVector(indices=indices, values=[counts[i] for i in indices])

    def embed_documents(self, texts: list[str]) -> list[models.SparseVector]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> models.SparseVector:
        return self._vector(text)
