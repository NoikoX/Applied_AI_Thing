"""Service layer shared by the REST API and the Gradio UI.

Validation, limits and permissions live here, once, so the two front ends
behave the same. Errors carry the HTTP status the API should return.
"""

import hmac
from dataclasses import dataclass, field
from typing import Protocol

from qdrant_client import QdrantClient

from investigator.api.limits import LimitExceeded, RequestLimiter
from investigator.config import AppConfig, AppSettings, Secrets
from investigator.index.registry import DocumentIndex, IngestResult
from investigator.ingestion.loaders import EmptyDocumentError, UnsupportedFormatError, load_bytes
from investigator.rag.schemas import RAGAnswer


class ServiceError(Exception):
    status_code = 400


class BadRequest(ServiceError):
    status_code = 400


class Forbidden(ServiceError):
    status_code = 403


class NotFound(ServiceError):
    status_code = 404


class TooLarge(ServiceError):
    status_code = 413


class RateLimited(ServiceError):
    status_code = 429


class QA(Protocol):
    def answer(self, question: str) -> RAGAnswer: ...


MAX_QUESTION_CHARS = 500


@dataclass
class Services:
    qdrant: QdrantClient
    index: DocumentIndex
    systems: dict[str, QA]  # "agent", "baseline"
    settings: AppSettings
    admin_token: str
    ask_limiter: RequestLimiter
    upload_limiter: RequestLimiter
    extra_status: dict = field(default_factory=dict)

    def ask(self, question: str, mode: str, client: str) -> RAGAnswer:
        question = (question or "").strip()
        if not 3 <= len(question) <= MAX_QUESTION_CHARS:
            raise BadRequest(f"Questions must be 3-{MAX_QUESTION_CHARS} characters long.")
        if mode not in self.systems:
            raise BadRequest(f"Unknown mode '{mode}'. Use one of: {', '.join(self.systems)}.")
        try:
            self.ask_limiter.check(client)
        except LimitExceeded as err:
            raise RateLimited(str(err)) from err
        return self.systems[mode].answer(question)

    def upload(self, filename: str, data: bytes, client: str) -> IngestResult:
        max_bytes = int(self.settings.max_upload_mb * 1024 * 1024)
        if len(data) > max_bytes:
            raise TooLarge(f"File is larger than {self.settings.max_upload_mb} MB.")
        try:
            doc = load_bytes(filename, data)  # format check before spending the upload allowance
        except (UnsupportedFormatError, EmptyDocumentError) as err:
            raise BadRequest(str(err)) from err
        try:
            self.upload_limiter.check(client)
        except LimitExceeded as err:
            raise RateLimited(str(err)) from err
        return self.index.add(doc)

    def delete(self, doc_id: str, admin_token: str | None) -> None:
        """Uploaded documents (up_...) can be deleted by anyone; corpus documents need the
        admin token, so a visitor cannot empty the demo's dataset."""
        if not doc_id.startswith("up_") and not self._is_admin(admin_token):
            raise Forbidden("Only uploaded documents can be deleted without the admin token.")
        if not self.index.delete(doc_id):
            raise NotFound(f"No document {doc_id}.")

    def get_document(self, doc_id: str) -> dict:
        entry = self.index.get(doc_id)
        if entry is None:
            raise NotFound(f"No document {doc_id}.")
        return entry

    def list_documents(self, limit: int = 50, offset: str | None = None):
        return self.index.list_documents(limit=min(max(limit, 1), 200), offset=offset)

    def _is_admin(self, token: str | None) -> bool:
        # compare_digest: constant-time, so the token cannot be guessed from response times
        return bool(token) and hmac.compare_digest(token, self.admin_token)


def build_services(cfg: AppConfig, secrets: Secrets) -> Services:
    """Production wiring: Qdrant Cloud, OpenAI embeddings, local ONNX models, LLM gateway."""
    from investigator.agent.graph import InvestigationAgent
    from investigator.agent.nodes import Deps
    from investigator.index.embeddings import make_openai_embedder
    from investigator.index.qdrant_store import connect, ensure_collections
    from investigator.index.sparse import BM25Encoder
    from investigator.llm.gateway import make_gateway
    from investigator.rag.baseline import BaselineRAG
    from investigator.retrieval.local_models import load_local_models, warm_up
    from investigator.retrieval.rerank import CrossEncoderReranker
    from investigator.retrieval.search import HybridRetriever

    client = connect(secrets)
    embedder = make_openai_embedder(secrets, cfg.embeddings)
    local = load_local_models(cfg.local_models)
    warm_up(local)
    sparse = BM25Encoder(local.sparse)
    name, strategy = cfg.app.index_name, cfg.index.chunking_strategy
    # Creates empty collections on a fresh cluster, so the app starts before data is loaded.
    ensure_collections(client, strategy, embedder.model, embedder.dimensions, index_name=name)
    index = DocumentIndex(
        client,
        strategy,
        cfg.chunking,
        embedder,
        sparse,
        cfg.index.near_duplicate_threshold,
        index_name=name,
    )
    retriever = HybridRetriever(
        client, name, cfg.retrieval, embedder, sparse, CrossEncoderReranker(local.reranker)
    )
    gateway = make_gateway(cfg.llm, secrets)
    systems = {
        "agent": InvestigationAgent(Deps(gateway, retriever, cfg.agent, cfg.rag.min_relevance)),
        "baseline": BaselineRAG(retriever, gateway, cfg.rag.min_relevance),
    }
    limits = cfg.app.limits
    return Services(
        qdrant=client,
        index=index,
        systems=systems,
        settings=cfg.app,
        admin_token=secrets.admin_token.get_secret_value(),
        ask_limiter=RequestLimiter(
            limits.ask_per_minute_per_client,
            limits.ask_per_day_per_client,
            limits.ask_per_day_total,
        ),
        upload_limiter=RequestLimiter(
            limits.uploads_per_day_per_client, limits.uploads_per_day_per_client
        ),
        extra_status={"gateway": gateway},
    )
