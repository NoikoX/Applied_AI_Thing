"""Cross-encoder reranking."""

import math
from typing import Protocol

from fastembed.rerank.cross_encoder import TextCrossEncoder


class Reranker(Protocol):
    def score(self, query: str, texts: list[str]) -> list[float]:
        """Relevance of each text to the query, 0..1."""
        ...


class CrossEncoderReranker:
    """Reads (query, passage) together, so it sees word interactions that two
    separate embeddings cannot. Too slow for the whole corpus, so it only
    rescores the top fused candidates.

    The model outputs logits (roughly -10..10); a sigmoid maps them to 0..1.
    Unlike min-max, that keeps an absolute meaning across queries, which the
    insufficient-evidence check relies on ("even the best chunk scores 0.02").

    Small batches keep memory flat: a batch is padded to its longest passage, and
    attention memory grows with batch x length^2 (see config local_models).
    """

    def __init__(self, model: TextCrossEncoder, batch_size: int = 4):
        self._model = model
        self.batch_size = batch_size

    def score(self, query: str, texts: list[str]) -> list[float]:
        logits = self._model.rerank(query, texts, batch_size=self.batch_size)
        return [1.0 / (1.0 + math.exp(-logit)) for logit in logits]
