import pydantic
import pytest

from investigator.config import load_config
from investigator.evaluation.retrieval_eval import (
    CachedQueryEmbedder,
    CachedReranker,
    apply_overrides,
    summarize,
)
from tests.fakes import FakeReranker, HashEmbedder

BASE = load_config().retrieval


def test_overrides_merge_nested_sections():
    cfg = apply_overrides(BASE, {"mode": "dense", "coverage": {"redundancy_lambda": 0.0}})
    assert cfg.mode == "dense"
    assert cfg.coverage.redundancy_lambda == 0.0
    assert cfg.coverage.w_cov == BASE.coverage.w_cov  # untouched siblings kept


def test_typo_in_override_fails():
    with pytest.raises(pydantic.ValidationError):
        apply_overrides(BASE, {"rerank_topn": 5})
    with pytest.raises(pydantic.ValidationError):
        apply_overrides(BASE, {"coverage": {"lambda": 0.1}})


def test_query_embeddings_are_cached():
    inner = HashEmbedder()
    cached = CachedQueryEmbedder(inner)
    first = cached.embed_queries(["a b", "c d"])
    again = cached.embed_queries(["c d", "a b", "a b"])
    assert again == [first[1], first[0], first[0]]
    assert len(inner.calls) == 1


class CountingReranker(FakeReranker):
    def __init__(self):
        self.pairs = 0

    def score(self, query, texts):
        self.pairs += len(texts)
        return super().score(query, texts)


def test_reranker_scores_are_cached_on_disk(tmp_path):
    inner = CountingReranker()
    path = tmp_path / "rerank.sqlite"
    first = CachedReranker(inner, "m", path).score("q a", ["a b", "c d"])
    again = CachedReranker(inner, "m", path)  # a new run, same file
    assert again.score("q a", ["c d", "a b", "e f"]) == [first[1], first[0], 0.0]
    assert inner.pairs == 3  # only "e f" was new
    assert (again.hits, again.misses) == (2, 1)


def test_reranker_cache_is_per_model(tmp_path):
    inner = CountingReranker()
    CachedReranker(inner, "model-1", tmp_path / "r.sqlite").score("q", ["x"])
    CachedReranker(inner, "model-2", tmp_path / "r.sqlite").score("q", ["x"])
    assert inner.pairs == 2


def test_summarize_overall_and_per_type():
    rows = [
        {"id": "1", "type": "bridge", "recall@5": 1.0, "full@5": True, "sent": None, "top": ["x"]},
        {"id": "2", "type": "bridge", "recall@5": 0.5, "full@5": False, "sent": 0.5, "top": []},
        {"id": "3", "type": "comparison", "recall@5": 0.0, "full@5": False, "sent": 1.0, "top": []},
    ]
    s = summarize(rows)
    assert s["all"]["n"] == 3
    assert s["all"]["recall@5"] == 0.5
    assert s["all"]["full@5"] == pytest.approx(1 / 3, abs=1e-4)
    assert s["all"]["sent"] == 0.75  # None skipped
    assert s["bridge"]["recall@5"] == 0.75 and s["comparison"]["n"] == 1
    assert "top" not in s["all"]  # lists are not averaged
