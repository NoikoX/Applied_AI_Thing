import pytest
from qdrant_client import QdrantClient

from investigator.config import load_config
from investigator.index.qdrant_store import IndexMismatchError, ensure_collections
from investigator.index.registry import DocumentIndex
from investigator.ingestion.documents import Document, Section
from investigator.retrieval.search import HybridRetriever
from tests.fakes import FakeReranker, FakeSparse, HashEmbedder

CFG = load_config()

PARAGRAPHS = {
    "Emmett's Mark": "Emmett's Mark is a 2002 thriller film starring John Doman and Scott Wolf.",
    "John Doman": "John Doman is an American actor who played William Rawls in The Wire on HBO.",
    "The Wire": "The Wire is an HBO crime drama series created by David Simon set in Baltimore.",
    "Seine": "The Seine is a river in northern France that flows through Paris.",
    "Paris": "Paris is the capital of France and its largest city on the Seine.",
}


@pytest.fixture(scope="module")
def setup():
    client = QdrantClient(":memory:")
    embedder = HashEmbedder()
    ensure_collections(client, "paragraph", embedder.model, embedder.dimensions)
    index = DocumentIndex(client, "paragraph", CFG.chunking, embedder, FakeSparse(), 0.95)
    docs = [
        Document(f"hp_{t}", t, "hotpotqa", "hotpotqa", [Section(text)], sentences=[text])
        for t, text in PARAGRAPHS.items()
    ]
    index.add_many(docs)
    return client, embedder


def retriever(setup, **overrides):
    client, embedder = setup
    cfg = CFG.retrieval.model_copy(update={"final_k": 3, **overrides})
    return HybridRetriever(client, "paragraph", cfg, embedder, FakeSparse(), FakeReranker())


@pytest.mark.parametrize("mode", ["dense", "sparse", "hybrid"])
@pytest.mark.parametrize("fusion", ["rrf", "weighted"])
def test_every_mode_finds_the_obvious_paragraph(setup, mode, fusion):
    result = retriever(setup, mode=mode, fusion=fusion).search("river in northern France")
    assert result.chunks[0].title == "Seine"


@pytest.mark.parametrize("selection", ["topk", "coverage"])
@pytest.mark.parametrize("rerank", [True, False])
def test_every_selection_returns_final_k_chunks(setup, selection, rerank):
    result = retriever(setup, selection=selection, rerank=rerank).search("HBO series The Wire")
    assert len(result.chunks) == 3
    assert len({c.chunk_id for c in result.chunks}) == 3
    assert all(c.ce is not None for c in result.chunks) == rerank


def test_subqueries_mark_coverage_and_bring_in_second_hop(setup):
    result = retriever(setup).search(
        "Which Emmett's Mark actor also played in The Wire?",
        subqueries=["Who starred in Emmett's Mark?", "Which actor played in The Wire on HBO?"],
    )
    titles = [c.title for c in result.chunks]
    assert "Emmett's Mark" in titles and "John Doman" in titles
    covered = set().union(*(c.covers for c in result.chunks))
    assert covered == {1, 2}


def test_result_reports_timings_and_pool_size(setup):
    result = retriever(setup).search("Paris")
    assert set(result.timings_ms) == {"embed", "search", "rerank", "select"}
    assert result.n_candidates == len(PARAGRAPHS)  # tiny index: everything is a candidate


def test_searching_an_index_built_with_another_model_is_rejected(setup):
    client, _ = setup
    other = HashEmbedder()
    other.model = "some-other-model"
    with pytest.raises(IndexMismatchError, match="some-other-model"):
        HybridRetriever(client, "paragraph", CFG.retrieval, other, FakeSparse(), FakeReranker())


def test_rerank_enabled_without_reranker_is_rejected(setup):
    client, embedder = setup
    with pytest.raises(ValueError, match="reranker"):
        HybridRetriever(client, "paragraph", CFG.retrieval, embedder, FakeSparse(), None)
