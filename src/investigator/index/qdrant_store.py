"""Qdrant connection and collection layout.

Two collections per chunking strategy:
  chunks_<strategy>  one point per chunk, named vectors "dense" (OpenAI) and "bm25" (sparse)
  docs_<strategy>    the document registry: one payload-only point per document
"""

import uuid

from qdrant_client import QdrantClient, models

from investigator.config import Secrets

DENSE = "dense"
SPARSE = "bm25"

# Fixed namespace so a document always maps to the same registry point ID.
REGISTRY_NAMESPACE = uuid.UUID("0b7d4c9e-3f21-4e8a-b6d5-91a2c7e4f013")


class IndexMismatchError(RuntimeError):
    """An existing collection was built with a different embedding model or size."""


def connect(secrets: Secrets, timeout: int = 10) -> QdrantClient:
    return QdrantClient(
        url=secrets.qdrant_url,
        api_key=secrets.qdrant_api_key.get_secret_value(),
        timeout=timeout,
    )


def chunks_collection(strategy: str) -> str:
    return f"chunks_{strategy}"


def registry_collection(strategy: str) -> str:
    return f"docs_{strategy}"


def registry_point_id(doc_id: str) -> str:
    return str(uuid.uuid5(REGISTRY_NAMESPACE, doc_id))


def ensure_collections(
    client: QdrantClient, strategy: str, embedding_model: str, dimensions: int
) -> None:
    """Create both collections if missing; refuse to reuse one built with another model.

    Vectors from different embedding models are not comparable, so silently
    mixing them would make search results meaningless.
    """
    chunks = chunks_collection(strategy)
    expected = {"embedding_model": embedding_model, "dimensions": dimensions}
    if client.collection_exists(chunks):
        meta = client.get_collection(chunks).config.metadata or {}
        found = {k: meta.get(k) for k in expected}
        if found != expected:
            raise IndexMismatchError(f"'{chunks}' was built with {found}, config says {expected}")
    else:
        client.create_collection(
            chunks,
            vectors_config={
                DENSE: models.VectorParams(size=dimensions, distance=models.Distance.COSINE)
            },
            sparse_vectors_config={SPARSE: models.SparseVectorParams(modifier=models.Modifier.IDF)},
            metadata={**expected, "chunking_strategy": strategy},
        )
        # Indexes for the filters the registry uses (delete by doc_id, drop old versions).
        # Qdrant Cloud may also refuse filters on fields that have no index.
        client.create_payload_index(chunks, "doc_id", models.PayloadSchemaType.KEYWORD)
        client.create_payload_index(chunks, "version", models.PayloadSchemaType.INTEGER)

    registry = registry_collection(strategy)
    if not client.collection_exists(registry):
        client.create_collection(registry, vectors_config={})
        client.create_payload_index(registry, "content_hash", models.PayloadSchemaType.KEYWORD)
