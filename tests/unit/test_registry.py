import pytest
from qdrant_client import QdrantClient

from investigator.config import load_config
from investigator.index.qdrant_store import IndexMismatchError, ensure_collections
from investigator.index.registry import DocumentIndex
from investigator.ingestion.chunking import chunk_id_for
from investigator.ingestion.documents import Document, Section
from tests.fakes import FakeSparse, HashEmbedder

CFG = load_config()

LONG = (
    "The payment service slowed down in March after the queue configuration was changed "
    "by the platform team during the database migration and the retry limit was lowered "
    "which caused card authorisations to time out for several hours across all regions"
)


def upload(name: str, *paragraphs: str) -> Document:
    return Document(
        doc_id=f"up_{name}",
        title=name,
        source=f"{name}.txt",
        format="txt",
        sections=[Section("\n\n".join(paragraphs))],
    )


@pytest.fixture
def embedder():
    return HashEmbedder()


@pytest.fixture
def index(embedder):
    """Uploads split by paragraph here, so each test controls its chunk boundaries exactly."""
    client = QdrantClient(":memory:")
    ensure_collections(client, "paragraph", embedder.model, embedder.dimensions)
    chunking = CFG.chunking.model_copy(update={"upload_strategy": "paragraph"})
    return DocumentIndex(
        client, "paragraph", chunking, embedder, FakeSparse(), near_duplicate_threshold=0.95
    )


def test_add_indexes_chunks_and_registers_document(index):
    result = index.add(upload("a", "First paragraph.", "Second paragraph."))
    assert (result.status, result.n_chunks) == ("added", 2)
    assert index.count_chunks("up_a") == 2
    entry = index.get("up_a")
    assert entry["version"] == 1 and entry["n_chunks"] == 2 and entry["format"] == "txt"


def test_uploads_use_upload_strategy_and_corpus_uses_collection_strategy():
    client = QdrantClient(":memory:")
    embedder = HashEmbedder()
    ensure_collections(client, "sentence_window", embedder.model, embedder.dimensions)
    index = DocumentIndex(
        client,
        "sentence_window",
        CFG.chunking,
        embedder,
        FakeSparse(),
        near_duplicate_threshold=0.95,
    )
    five = ["One.", "Two.", "Three.", "Four.", "Five."]
    corpus = Document(
        "hp_1", "T", "hotpotqa", "hotpotqa", [Section(" ".join(five))], sentences=five
    )
    assert index.add(corpus).n_chunks == 2  # sentence windows (0-3) and (2-5)
    # The same five short sentences as an upload: one recursive chunk (< chunk_size characters).
    assert index.add(upload("u", " ".join(five))).n_chunks == 1


def test_unchanged_document_is_not_embedded_again(index, embedder):
    index.add(upload("a", "Same text."))
    calls = len(embedder.calls)
    assert index.add(upload("a", "Same text.")).status == "unchanged"
    assert len(embedder.calls) == calls


def test_update_replaces_chunks_and_keeps_created_at(index):
    index.add(upload("a", "One.", "Two.", "Three."))
    created = index.get("up_a")["created_at"]
    result = index.add(upload("a", "Only one paragraph now."))
    assert (result.status, result.n_chunks) == ("updated", 1)
    assert index.count_chunks("up_a") == 1  # old chunks 1 and 2 removed
    entry = index.get("up_a")
    assert entry["version"] == 2 and entry["created_at"] == created


def test_same_content_under_another_name_is_a_duplicate(index):
    index.add(upload("a", "Identical content."))
    doc = upload("b", "Identical content.")
    doc.title = "a"  # the content hash covers title + text
    result = index.add(doc)
    assert (result.status, result.duplicate_of) == ("duplicate", "up_a")
    assert index.get("up_b") is None and index.count_chunks("up_b") == 0


def test_near_duplicate_chunk_is_not_indexed_again(index):
    index.add(upload("a", LONG))
    result = index.add(upload("b", LONG + " today", "A genuinely new paragraph."))
    assert (result.n_chunks, result.n_near_duplicates) == (1, 1)
    # Chunk 0 of b points at chunk 0 of a; only b's new paragraph (chunk 1) was indexed.
    assert index.get("up_b")["near_duplicates"] == {"0": chunk_id_for("up_a", 0)}
    assert index.count_chunks("up_b") == 1


def test_near_duplicate_check_ignores_the_document_itself(index):
    index.add(upload("a", LONG))
    result = index.add(upload("a", LONG + " today"))  # an update, not a duplicate
    assert (result.status, result.n_chunks, result.n_near_duplicates) == ("updated", 1, 0)


def test_delete_removes_chunks_and_entry(index):
    index.add(upload("a", "x one.", "y two."))
    assert index.delete("up_a") is True
    assert index.get("up_a") is None and index.count_chunks("up_a") == 0
    assert index.delete("up_a") is False


def test_add_many_batches_embedding_calls_and_is_idempotent(index, embedder):
    docs = [upload(f"d{i}", f"paragraph number {i}") for i in range(5)]
    results = index.add_many(docs, batch_size=10)
    assert [r.status for r in results] == ["added"] * 5
    assert len(embedder.calls) == 1  # one API call for the whole batch
    assert [r.status for r in index.add_many(docs)] == ["unchanged"] * 5
    assert len(embedder.calls) == 1


def test_list_documents_pages_through_registry(index):
    for i in range(3):
        index.add(upload(f"d{i}", f"text {i}"))
    page, next_offset = index.list_documents(limit=2)
    rest, end = index.list_documents(limit=2, offset=next_offset)
    assert len(page) == 2 and len(rest) == 1 and end is None


def test_collection_built_with_other_model_is_rejected():
    client = QdrantClient(":memory:")
    ensure_collections(client, "paragraph", "model-a", 8)
    ensure_collections(client, "paragraph", "model-a", 8)  # same settings: fine
    with pytest.raises(IndexMismatchError, match="model-b"):
        ensure_collections(client, "paragraph", "model-b", 8)
