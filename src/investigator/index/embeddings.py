"""Dense embeddings via the OpenAI API."""

import time
from collections.abc import Callable
from typing import Protocol

from openai import OpenAI

from investigator.config import EmbeddingConfig, Secrets
from investigator.llm.errors import LLMError
from investigator.llm.retry import RetryPolicy, call_with_retries


class EmbeddingError(RuntimeError):
    """The embedding API failed for good (quota, bad request, or retries used up)."""


class DenseEmbedder(Protocol):
    model: str
    dimensions: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed documents/chunks."""
        ...

    def embed_queries(self, queries: list[str]) -> list[list[float]]:
        """Embed search queries. Same as documents for OpenAI; kept separate because
        some models (e.g. bge) expect an instruction prefix on queries."""
        ...


class OpenAIEmbedder:
    """Embeds texts in batches.

    Retries use the same hand-written policy as the LLM gateway (the SDK's own
    retries are off): backoff on rate limits, 5xx and timeouts, but no retry on
    "out of quota/billing" 429s, which the SDK would otherwise retry pointlessly.
    The final failure becomes an EmbeddingError. Queries and documents use the same call.
    """

    def __init__(
        self,
        client: OpenAI,
        cfg: EmbeddingConfig,
        policy: RetryPolicy,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self._client = client
        self.model = cfg.name
        self.dimensions = cfg.dimensions
        self.batch_size = cfg.batch_size
        self.policy = policy
        self.sleep = sleep
        self.tokens_used = 0

    def embed(self, texts: list[str]) -> list[list[float]]:
        if any(not t.strip() for t in texts):
            raise ValueError("Cannot embed empty text")
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            try:
                resp, _ = call_with_retries(
                    lambda b=batch: self._client.embeddings.create(
                        model=self.model, input=b, dimensions=self.dimensions
                    ),
                    self.policy,
                    sleep=self.sleep,
                )
            except LLMError as err:
                raise EmbeddingError(f"Embedding request failed: {err}") from err
            self.tokens_used += resp.usage.total_tokens
            # The API returns one item per input with its position; sort to be safe.
            vectors.extend(d.embedding for d in sorted(resp.data, key=lambda d: d.index))
        return vectors

    def embed_queries(self, queries: list[str]) -> list[list[float]]:
        return self.embed(queries)


def make_openai_embedder(
    secrets: Secrets, cfg: EmbeddingConfig, comparison: bool = False
) -> OpenAIEmbedder:
    """comparison=True uses the comparison model (offline evaluation only)."""
    if comparison:
        cfg = cfg.model_copy(update={"name": cfg.comparison_name})
    client = OpenAI(api_key=secrets.openai_api_key.get_secret_value(), max_retries=0, timeout=30)
    policy = RetryPolicy(max_attempts=cfg.max_retries + 1, backoff_base_s=2.0, backoff_max_s=30.0)
    return OpenAIEmbedder(client, cfg, policy)
