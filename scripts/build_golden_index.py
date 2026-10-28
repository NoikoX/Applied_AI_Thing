"""Build the golden evaluation index from eval/golden/index_plan.json.

    uv run python scripts/build_golden_index.py

1. copy the base index (local Qdrant) to the golden index
2. delete the paragraphs that make some questions unanswerable  (registry delete)
3. upload the synthetic PDF/DOCX/Markdown/HTML/text documents   (the upload pipeline)
Steps 2-3 go through the same DocumentIndex code the app uses, so building
this index also exercises delete, file loading, chunking and duplicate checks.
"""

import json

from qdrant_client import QdrantClient

from investigator.config import PROJECT_ROOT, load_config, load_secrets
from investigator.index.embeddings import make_openai_embedder
from investigator.index.qdrant_store import (
    chunks_collection,
    copy_collection,
    registry_collection,
)
from investigator.index.registry import DocumentIndex
from investigator.index.sparse import BM25Encoder
from investigator.ingestion.loaders import load_bytes
from investigator.retrieval.local_models import load_local_models

GOLDEN = PROJECT_ROOT / "eval" / "golden"


def main() -> None:
    plan = json.loads((GOLDEN / "index_plan.json").read_text(encoding="utf-8"))
    cfg, secrets = load_config(), load_secrets()
    client = QdrantClient(url="http://localhost:6333", timeout=120)
    base, golden = plan["base_index"], plan["golden_index"]

    for name in (chunks_collection, registry_collection):
        n = copy_collection(client, name(base), client, name(golden))
        print(f"copied {name(base)} -> {name(golden)}: {n} points", flush=True)

    index = DocumentIndex(
        client, cfg.index.chunking_strategy, cfg.chunking,
        make_openai_embedder(secrets, cfg.embeddings),
        BM25Encoder(load_local_models(cfg.local_models).sparse),
        cfg.index.near_duplicate_threshold, index_name=golden,
    )  # fmt: skip
    for doc_id in plan["remove_doc_ids"]:
        print(f"delete {doc_id}: {index.delete(doc_id)}")
    for filename in plan["uploads"]:
        doc = load_bytes(filename, (GOLDEN / "docs" / filename).read_bytes())
        r = index.add(doc)
        print(f"upload {filename} ({doc.format}, title {doc.title!r}): {r.status}, "
              f"{r.n_chunks} chunks, near-duplicates {r.n_near_duplicates}, "
              f"possible conflicts {r.n_possible_conflicts}")  # fmt: skip


if __name__ == "__main__":
    main()
