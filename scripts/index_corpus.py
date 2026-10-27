"""Index data/corpus.jsonl into Qdrant with one chunking strategy and one embedding model.

Usage (local Qdrant in Docker for experiments):
    uv run python scripts/index_corpus.py --strategy paragraph --embedder openai \
        --qdrant-url http://localhost:6333

Re-running is safe: documents already indexed with the same content are skipped.
"""

import argparse
import json
import time

from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient

from investigator.config import PROJECT_ROOT, load_config, load_secrets
from investigator.index.embeddings import make_openai_embedder
from investigator.index.qdrant_store import connect, ensure_collections
from investigator.index.registry import DocumentIndex
from investigator.index.sparse import BM25Encoder
from investigator.ingestion.loaders import load_corpus_record

BATCH_DOCS = 1024  # documents per progress step (add_many batches embedding calls inside)


def index_name_for(strategy: str, embedder: str) -> str:
    """Production model -> "paragraph"; comparison model -> "paragraph__comparison"."""
    return strategy if embedder == "production" else f"{strategy}__comparison"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", choices=["paragraph", "sentence_window"], required=True)
    parser.add_argument("--embedder", choices=["production", "comparison"], default="production")
    parser.add_argument("--qdrant-url", help="defaults to QDRANT_URL from the environment")
    parser.add_argument("--limit", type=int, help="index only the first N documents")
    args = parser.parse_args()

    cfg, secrets = load_config(), load_secrets()
    client = QdrantClient(url=args.qdrant_url, timeout=60) if args.qdrant_url else connect(secrets)
    embedder = make_openai_embedder(
        secrets, cfg.embeddings, comparison=args.embedder == "comparison"
    )
    lm = cfg.local_models
    sparse = BM25Encoder(SparseTextEmbedding(lm.sparse, cache_dir=str(PROJECT_ROOT / lm.cache_dir)))

    name = index_name_for(args.strategy, args.embedder)
    ensure_collections(client, args.strategy, embedder.model, embedder.dimensions, index_name=name)
    index = DocumentIndex(
        client, args.strategy, cfg.chunking, embedder, sparse,
        cfg.index.near_duplicate_threshold, index_name=name,
    )  # fmt: skip

    with open(PROJECT_ROOT / "data" / "corpus.jsonl", encoding="utf-8") as f:
        docs = [load_corpus_record(json.loads(line)) for line in f]
    docs = docs[: args.limit] if args.limit else docs

    start, statuses, n_chunks = time.time(), {}, 0
    for i in range(0, len(docs), BATCH_DOCS):
        for r in index.add_many(docs[i : i + BATCH_DOCS]):
            statuses[r.status] = statuses.get(r.status, 0) + 1
            n_chunks += r.n_chunks
        done = min(i + BATCH_DOCS, len(docs))
        tokens = getattr(embedder, "tokens_used", 0)
        print(f"{done}/{len(docs)} docs | {n_chunks} chunks | {tokens} tokens | "
              f"{time.time() - start:.0f}s", flush=True)  # fmt: skip

    print(json.dumps({"index": name, "documents": statuses, "chunks": n_chunks}, indent=2))


if __name__ == "__main__":
    main()
