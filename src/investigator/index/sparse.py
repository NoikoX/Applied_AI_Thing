"""BM25 sparse vectors for keyword search."""

from typing import Protocol

from fastembed import SparseTextEmbedding
from qdrant_client import models


class SparseEncoder(Protocol):
    def embed_documents(self, texts: list[str]) -> list[models.SparseVector]: ...

    def embed_query(self, text: str) -> models.SparseVector: ...


class BM25Encoder:
    """Term weights from fastembed's BM25 model.

    The IDF part of BM25 is applied by Qdrant at query time (the collection is
    created with Modifier.IDF), so adding documents never requires recomputing
    the vectors of documents already indexed.
    """

    def __init__(self, model: SparseTextEmbedding):
        self._model = model

    def embed_documents(self, texts: list[str]) -> list[models.SparseVector]:
        return [_to_qdrant(e) for e in self._model.embed(texts)]

    def embed_query(self, text: str) -> models.SparseVector:
        return _to_qdrant(next(iter(self._model.query_embed(text))))


def _to_qdrant(embedding) -> models.SparseVector:
    return models.SparseVector(indices=embedding.indices.tolist(), values=embedding.values.tolist())
