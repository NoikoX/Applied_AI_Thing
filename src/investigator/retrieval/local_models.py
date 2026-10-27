"""Local ONNX models run in-process via fastembed: BM25 sparse encoder and reranker."""

from dataclasses import dataclass

from fastembed import SparseTextEmbedding
from fastembed.rerank.cross_encoder import TextCrossEncoder

from investigator.config import PROJECT_ROOT, LocalModelsConfig, load_config


@dataclass
class LocalModels:
    sparse: SparseTextEmbedding
    reranker: TextCrossEncoder


def load_local_models(cfg: LocalModelsConfig) -> LocalModels:
    cache_dir = str(PROJECT_ROOT / cfg.cache_dir)
    return LocalModels(
        sparse=SparseTextEmbedding(cfg.sparse, cache_dir=cache_dir, threads=cfg.threads),
        reranker=TextCrossEncoder(cfg.reranker, cache_dir=cache_dir, threads=cfg.threads),
    )


def warm_up(models: LocalModels, n_docs: int = 30) -> None:
    """Run one query through each model.

    The first real request is then not slow, and memory readings reflect a
    realistic query (rerank of 30 candidates), not just idle models.
    """
    list(models.sparse.query_embed("warm up query"))
    docs = ["A short passage used to warm up the reranker."] * n_docs
    list(models.reranker.rerank("warm up query", docs))


if __name__ == "__main__":
    # Used by the Dockerfile to download the models at build time.
    load_local_models(load_config().local_models)
