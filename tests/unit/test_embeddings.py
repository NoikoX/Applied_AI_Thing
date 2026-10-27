from types import SimpleNamespace

import openai
import pytest

from investigator.config import load_config
from investigator.index.embeddings import EmbeddingError, OpenAIEmbedder

CFG = load_config().embeddings.model_copy(update={"batch_size": 2, "dimensions": 3})


class FakeEmbeddingsAPI:
    """Mimics client.embeddings.create; returns items in reverse order on purpose."""

    def __init__(self, fail: bool = False):
        self.fail = fail
        self.requests: list[dict] = []

    def create(self, model, input, dimensions):
        self.requests.append({"model": model, "input": input, "dimensions": dimensions})
        if self.fail:
            raise openai.APIConnectionError(request=None)
        data = [
            SimpleNamespace(index=i, embedding=[float(len(text))] * dimensions)
            for i, text in enumerate(input)
        ]
        return SimpleNamespace(data=data[::-1], usage=SimpleNamespace(total_tokens=10))


def make(fail: bool = False):
    api = FakeEmbeddingsAPI(fail)
    return OpenAIEmbedder(SimpleNamespace(embeddings=api), CFG), api


def test_batches_requests_and_keeps_input_order():
    embedder, api = make()
    vectors = embedder.embed(["a", "bb", "ccc"])
    assert [len(r["input"]) for r in api.requests] == [2, 1]
    assert [v[0] for v in vectors] == [1.0, 2.0, 3.0]  # order restored despite reversed reply
    assert api.requests[0]["model"] == CFG.name and api.requests[0]["dimensions"] == 3
    assert embedder.tokens_used == 20


def test_api_failure_becomes_embedding_error():
    embedder, _ = make(fail=True)
    with pytest.raises(EmbeddingError):
        embedder.embed(["a"])


def test_empty_text_rejected_before_any_request():
    embedder, api = make()
    with pytest.raises(ValueError, match="empty"):
        embedder.embed(["ok", "  "])
    assert api.requests == []
