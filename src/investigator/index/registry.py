"""Document registry: add, update and delete documents and their chunks.

Write path for one document:
  1. Same doc_id and same content hash  -> "unchanged" (nothing re-embedded).
  2. Another doc_id has the same content -> "duplicate" (exact dedup, not indexed).
  3. Chunk, embed (dense + BM25), and drop chunks whose nearest chunk from
     another document is above the near-duplicate threshold.
  4. Upsert chunks with version v, then delete this document's chunks with a
     version below v. Chunk IDs are deterministic, so the upsert overwrites the
     old chunks in place, and the document is never left with zero chunks.
  5. Upsert the registry entry.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from qdrant_client import QdrantClient, models

from investigator.config import ChunkingConfig
from investigator.index.embeddings import DenseEmbedder
from investigator.index.qdrant_store import (
    DENSE,
    SPARSE,
    chunks_collection,
    registry_collection,
    registry_point_id,
)
from investigator.index.sparse import SparseEncoder
from investigator.ingestion.chunking import chunk_document
from investigator.ingestion.documents import Chunk, Document


@dataclass
class IngestResult:
    doc_id: str
    status: Literal["added", "updated", "unchanged", "duplicate"]
    n_chunks: int = 0
    n_near_duplicates: int = 0
    duplicate_of: str | None = None


def embedding_text(chunk: Chunk) -> str:
    """Text sent to the embedder and BM25.

    The title is prepended because paragraphs often refer to their subject only
    by pronoun ("He was born in ..."); the title puts the entity back.
    """
    return f"{chunk.title}\n{chunk.text}"


def _doc_filter(doc_id: str) -> models.Filter:
    return models.Filter(
        must=[models.FieldCondition(key="doc_id", match=models.MatchValue(value=doc_id))]
    )


class DocumentIndex:
    def __init__(
        self,
        client: QdrantClient,
        strategy: str,
        chunking: ChunkingConfig,
        dense: DenseEmbedder,
        sparse: SparseEncoder,
        near_duplicate_threshold: float,
    ):
        self.client = client
        self.strategy = strategy
        self.chunking = chunking
        self.dense = dense
        self.sparse = sparse
        self.threshold = near_duplicate_threshold
        self.chunks = chunks_collection(strategy)
        self.registry = registry_collection(strategy)

    # ---- reads -------------------------------------------------------------

    def get(self, doc_id: str) -> dict | None:
        points = self.client.retrieve(self.registry, [registry_point_id(doc_id)])
        return points[0].payload if points else None

    def list_documents(self, limit: int = 100, offset: str | None = None):
        """One page of registry entries and the offset of the next page (None at the end)."""
        points, next_offset = self.client.scroll(self.registry, limit=limit, offset=offset)
        return [p.payload for p in points], next_offset

    def count_chunks(self, doc_id: str) -> int:
        return self.client.count(self.chunks, count_filter=_doc_filter(doc_id)).count

    # ---- writes ------------------------------------------------------------

    def add(self, doc: Document, check_near_duplicates: bool = True) -> IngestResult:
        existing = self.get(doc.doc_id)
        content_hash = doc.content_hash
        if existing and existing["content_hash"] == content_hash:
            return IngestResult(doc.doc_id, "unchanged", existing["n_chunks"])

        same_content = self._find_by_hash(content_hash)
        if same_content and same_content["doc_id"] != doc.doc_id:
            return IngestResult(doc.doc_id, "duplicate", duplicate_of=same_content["doc_id"])

        version = existing["version"] + 1 if existing else 1
        chunks = self._chunk(doc)
        texts = [embedding_text(c) for c in chunks]
        dense = self.dense.embed(texts)
        sparse = self.sparse.embed_documents(texts)

        near_duplicates = {}
        if check_near_duplicates:
            for chunk, vector in zip(chunks, dense, strict=True):
                match = self._near_duplicate_of(vector, doc.doc_id)
                if match:
                    near_duplicates[str(chunk.index)] = match

        points = [
            self._chunk_point(chunk, d, s, doc, version)
            for chunk, d, s in zip(chunks, dense, sparse, strict=True)
            if str(chunk.index) not in near_duplicates
        ]
        if points:
            self.client.upsert(self.chunks, points)
        self._delete_versions_below(doc.doc_id, version)
        self._upsert_registry(doc, version, len(points), near_duplicates, existing)
        return IngestResult(
            doc.doc_id, "updated" if existing else "added", len(points), len(near_duplicates)
        )

    def add_many(self, docs: list[Document], batch_size: int = 256) -> list[IngestResult]:
        """Bulk ingest for the corpus: one embedding call per batch of documents.

        Skips the exact-duplicate lookup and the near-duplicate search, which
        cost one request per document. That is safe for the corpus because its
        doc IDs are content hashes, so identical content always has the same ID.
        """
        results: list[IngestResult] = []
        for start in range(0, len(docs), batch_size):
            batch = docs[start : start + batch_size]
            existing = {
                p.payload["doc_id"]: p.payload
                for p in self.client.retrieve(
                    self.registry, [registry_point_id(d.doc_id) for d in batch]
                )
            }
            new_docs = []
            for doc in batch:
                old = existing.get(doc.doc_id)
                if old and old["content_hash"] == doc.content_hash:
                    results.append(IngestResult(doc.doc_id, "unchanged", old["n_chunks"]))
                elif old:  # content changed under the same ID: take the careful path
                    results.append(self.add(doc, check_near_duplicates=False))
                else:
                    new_docs.append(doc)
            results.extend(self._index_new(new_docs))
        return results

    def delete(self, doc_id: str) -> bool:
        if self.get(doc_id) is None:
            return False
        self.client.delete(
            self.chunks, points_selector=models.FilterSelector(filter=_doc_filter(doc_id))
        )
        self.client.delete(
            self.registry, points_selector=models.PointIdsList(points=[registry_point_id(doc_id)])
        )
        return True

    # ---- helpers -----------------------------------------------------------

    def _chunk(self, doc: Document) -> list[Chunk]:
        """Corpus paragraphs use the collection's strategy (the one under evaluation);
        uploaded files are long and unlabelled, so they always use the upload strategy."""
        strategy = self.strategy if doc.format == "hotpotqa" else self.chunking.upload_strategy
        return chunk_document(doc, strategy, self.chunking)

    def _index_new(self, docs: list[Document]) -> list[IngestResult]:
        if not docs:
            return []
        per_doc = [self._chunk(d) for d in docs]
        all_chunks = [c for chunks in per_doc for c in chunks]
        texts = [embedding_text(c) for c in all_chunks]
        dense = iter(self.dense.embed(texts))
        sparse = iter(self.sparse.embed_documents(texts))

        points = [
            self._chunk_point(c, next(dense), next(sparse), doc, version=1)
            for doc, chunks in zip(docs, per_doc, strict=True)
            for c in chunks
        ]
        self.client.upsert(self.chunks, points)
        for doc, chunks in zip(docs, per_doc, strict=True):
            self._upsert_registry(doc, 1, len(chunks), {}, existing=None)
        return [IngestResult(d.doc_id, "added", len(c)) for d, c in zip(docs, per_doc, strict=True)]

    def _find_by_hash(self, content_hash: str) -> dict | None:
        points, _ = self.client.scroll(
            self.registry,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="content_hash", match=models.MatchValue(value=content_hash)
                    )
                ]
            ),
            limit=1,
        )
        return points[0].payload if points else None

    def _near_duplicate_of(self, vector: list[float], doc_id: str) -> str | None:
        """chunk_id of the most similar chunk from another document, if above the threshold."""
        hits = self.client.query_points(
            self.chunks,
            query=vector,
            using=DENSE,
            query_filter=models.Filter(
                must_not=[
                    models.FieldCondition(key="doc_id", match=models.MatchValue(value=doc_id))
                ]
            ),
            limit=1,
        ).points
        if hits and hits[0].score >= self.threshold:
            return str(hits[0].id)
        return None

    def _delete_versions_below(self, doc_id: str, version: int) -> None:
        self.client.delete(
            self.chunks,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(key="doc_id", match=models.MatchValue(value=doc_id)),
                        models.FieldCondition(key="version", range=models.Range(lt=version)),
                    ]
                )
            ),
        )

    def _chunk_point(
        self,
        chunk: Chunk,
        dense: list[float],
        sparse: models.SparseVector,
        doc: Document,
        version: int,
    ) -> models.PointStruct:
        return models.PointStruct(
            id=chunk.chunk_id,
            vector={DENSE: dense, SPARSE: sparse},
            payload={
                "doc_id": doc.doc_id,
                "chunk_index": chunk.index,
                "title": chunk.title,
                "text": chunk.text,
                "page": chunk.page,
                "sent_start": chunk.sent_start,
                "sent_end": chunk.sent_end,
                "source": doc.source,
                "format": doc.format,
                "version": version,
            },
        )

    def _upsert_registry(
        self,
        doc: Document,
        version: int,
        n_chunks: int,
        near_duplicates: dict[str, str],
        existing: dict | None,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        payload = {
            "doc_id": doc.doc_id,
            "title": doc.title,
            "source": doc.source,
            "format": doc.format,
            "metadata": doc.metadata,
            "content_hash": doc.content_hash,
            "version": version,
            "n_chunks": n_chunks,
            "near_duplicates": near_duplicates,  # chunk index -> chunk_id it duplicates
            "created_at": existing["created_at"] if existing else now,
            "updated_at": now,
        }
        self.client.upsert(
            self.registry,
            [models.PointStruct(id=registry_point_id(doc.doc_id), vector={}, payload=payload)],
        )
