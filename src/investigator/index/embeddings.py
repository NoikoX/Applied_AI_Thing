"""Dense embeddings via the OpenAI API."""

from typing import Protocol

import openai
from openai import OpenAI

from investigator.config import EmbeddingConfig, Secrets


class EmbeddingError(RuntimeError):
    """The embedding API failed even after the SDK's retries."""


class DenseEmbedder(Protocol):
    model: str
    dimensions: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIEmbedder:
    """Embeds texts in batches.

    Retries on rate limits (429), server errors and timeouts are done by the
    OpenAI SDK itself (`max_retries`, exponential backoff, honours Retry-After),
    so this class only batches, counts tokens and turns the final failure into
    an EmbeddingError. Queries and documents use the same model and call.
    """

    def __init__(self, client: OpenAI, cfg: EmbeddingConfig):
        self._client = client
        self.model = cfg.name
        self.dimensions = cfg.dimensions
        self.batch_size = cfg.batch_size
        self.tokens_used = 0

    def embed(self, texts: list[str]) -> list[list[float]]:
        if any(not t.strip() for t in texts):
            raise ValueError("Cannot embed empty text")
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            try:
                resp = self._client.embeddings.create(
                    model=self.model, input=batch, dimensions=self.dimensions
                )
            except openai.OpenAIError as err:
                raise EmbeddingError(f"Embedding request failed: {err}") from err
            self.tokens_used += resp.usage.total_tokens
            # The API returns one item per input with its position; sort to be safe.
            vectors.extend(d.embedding for d in sorted(resp.data, key=lambda d: d.index))
        return vectors


def make_openai_embedder(secrets: Secrets, cfg: EmbeddingConfig) -> OpenAIEmbedder:
    client = OpenAI(
        api_key=secrets.openai_api_key.get_secret_value(),
        max_retries=cfg.max_retries,
        timeout=30,
    )
    return OpenAIEmbedder(client, cfg)
