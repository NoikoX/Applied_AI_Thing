from types import SimpleNamespace

import openai
import pytest

from investigator.config import load_config
from investigator.index.embeddings import EmbeddingError, OpenAIEmbedder
from investigator.llm.retry import RetryPolicy

CFG = load_config().embeddings.model_copy(update={"batch_size": 2, "dimensions": 3})
POLICY = RetryPolicy(max_attempts=3, backoff_base_s=1.0, backoff_max_s=5.0)


class BillingError(Exception):
    """Shaped like OpenAI's 429 for an account without credit."""

    status_code = 429

    def __str__(self):
        return "Error code: 429 - Your account is not active, please check your billing details"


class FakeEmbeddingsAPI:
    """Mimics client.embeddings.create; returns items in reverse order on purpose."""

    def __init__(self, error: Exception | None = None):
        self.error = error
        self.requests: list[dict] = []

    def create(self, model, input, dimensions):
        self.requests.append({"model": model, "input": input, "dimensions": dimensions})
        if self.error:
            raise self.error
        data = [
            SimpleNamespace(index=i, embedding=[float(len(text))] * dimensions)
            for i, text in enumerate(input)
        ]
        return SimpleNamespace(data=data[::-1], usage=SimpleNamespace(total_tokens=10))


def make(error: Exception | None = None):
    api = FakeEmbeddingsAPI(error)
    embedder = OpenAIEmbedder(SimpleNamespace(embeddings=api), CFG, POLICY, sleep=lambda s: None)
    return embedder, api


def test_batches_requests_and_keeps_input_order():
    embedder, api = make()
    vectors = embedder.embed(["a", "bb", "ccc"])
    assert [len(r["input"]) for r in api.requests] == [2, 1]
    assert [v[0] for v in vectors] == [1.0, 2.0, 3.0]  # order restored despite reversed reply
    assert api.requests[0]["model"] == CFG.name and api.requests[0]["dimensions"] == 3
    assert embedder.tokens_used == 20


def test_connection_error_is_retried_then_becomes_embedding_error():
    embedder, api = make(openai.APIConnectionError(request=None))
    with pytest.raises(EmbeddingError):
        embedder.embed(["a"])
    assert len(api.requests) == POLICY.max_attempts


def test_billing_429_is_not_retried():
    embedder, api = make(BillingError())
    with pytest.raises(EmbeddingError, match="billing"):
        embedder.embed(["a"])
    assert len(api.requests) == 1


def test_empty_text_rejected_before_any_request():
    embedder, api = make()
    with pytest.raises(ValueError, match="empty"):
        embedder.embed(["ok", "  "])
    assert api.requests == []
