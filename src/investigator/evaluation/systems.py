"""Wire up the baseline or the agent against a local Qdrant index (evaluation scripts)."""

from qdrant_client import QdrantClient

from investigator.agent.graph import InvestigationAgent
from investigator.agent.nodes import Deps
from investigator.config import load_config, load_secrets, with_overrides
from investigator.index.embeddings import make_openai_embedder
from investigator.index.sparse import BM25Encoder
from investigator.llm.gateway import make_gateway
from investigator.rag.baseline import BaselineRAG
from investigator.retrieval.local_models import load_local_models
from investigator.retrieval.rerank import CrossEncoderReranker
from investigator.retrieval.search import HybridRetriever


def make_parts(
    generator: str, index: str, qdrant_url: str = "http://localhost:6333", deployed: bool = False
):
    """(gateway, retriever, judge_gateway, llm_config) for one generator setting.

    generator "gemini" uses the configured roles; any key of llm.comparison_generators
    ("nano", "mini") runs the planner, answer and grader roles on that model instead
    (the LLM comparison). The judge always uses the configured judge model.
    deployed=True applies app.retrieval_overrides, i.e. evaluates what the live demo runs.
    """
    cfg, secrets = load_config(), load_secrets()
    llm_cfg = cfg.llm
    if generator != "gemini":
        spec = cfg.llm.comparison_generators[generator]
        llm_cfg = cfg.llm.model_copy(update={"planner": spec, "answer": spec, "grader": spec})
    retrieval = with_overrides(cfg.retrieval, cfg.app.retrieval_overrides if deployed else {})
    local = load_local_models(
        cfg.local_models.model_copy(update={"threads": None}), with_reranker=retrieval.rerank
    )
    reranker = (
        CrossEncoderReranker(local.reranker, cfg.local_models.rerank_batch_size)
        if local.reranker is not None
        else None
    )
    retriever = HybridRetriever(
        QdrantClient(url=qdrant_url, timeout=60), index, retrieval,
        make_openai_embedder(secrets, cfg.embeddings), BM25Encoder(local.sparse), reranker,
    )  # fmt: skip
    return make_gateway(llm_cfg, secrets), retriever, make_gateway(cfg.llm, secrets), llm_cfg


def make_system(name: str, gateway, retriever):
    cfg = load_config()
    if name == "baseline":
        return BaselineRAG(retriever, gateway, cfg.rag.min_relevance)
    return InvestigationAgent(Deps(gateway, retriever, cfg.agent, cfg.rag.min_relevance))
