"""Copy the production index from the local Qdrant to Qdrant Cloud, reusing its embeddings.

    uv run python scripts/copy_index_to_cloud.py --source paragraph__large

Copies chunks_<source> -> chunks_<app.index_name> and docs_<source> -> docs_<app.index_name>
(vectors, payloads, metadata, payload indexes). No embedding API calls, so no cost.
The target collections are replaced.
"""

import argparse
import time

from qdrant_client import QdrantClient

from investigator.config import load_config, load_secrets
from investigator.index.qdrant_store import (
    check_embedding_model,
    chunks_collection,
    connect,
    copy_collection,
    registry_collection,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="local index name, e.g. paragraph__large")
    parser.add_argument("--local-url", default="http://localhost:6333")
    args = parser.parse_args()

    cfg, secrets = load_config(), load_secrets()
    local = QdrantClient(url=args.local_url, timeout=120)
    cloud = connect(secrets, timeout=120)
    target = cfg.app.index_name

    # Refuse to ship vectors from a different embedding model than production uses.
    check_embedding_model(local, chunks_collection(args.source), cfg.embeddings.name,
                          cfg.embeddings.dimensions)  # fmt: skip
    for name in (chunks_collection, registry_collection):
        start = time.time()
        n = copy_collection(local, name(args.source), cloud, name(target), batch=128)
        print(f"{name(args.source)} -> cloud {name(target)}: {n} points, "
              f"{time.time() - start:.0f}s", flush=True)  # fmt: skip
    print("cloud collections:", sorted(c.name for c in cloud.get_collections().collections))


if __name__ == "__main__":
    main()
