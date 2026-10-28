"""Single-pass RAG: retrieve once, answer once, verify, maybe refuse.

This is the baseline the multi-step agent is compared against in evaluation.
Failures of the search or the LLM never raise to the caller; they come back
as status "unavailable" with a message the UI can show.
"""

import logging
import time

from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

from investigator.index.embeddings import EmbeddingError
from investigator.llm.errors import LLMError
from investigator.llm.gateway import LLMGateway
from investigator.rag.citations import verify_citations
from investigator.rag.prompts import ANSWER_SYSTEM, PROMPT_VERSION, format_sources
from investigator.rag.schemas import Citation, LLMAnswer, RAGAnswer
from investigator.rag.sufficiency import check_before_llm, decide_after_llm
from investigator.retrieval.search import HybridRetriever

logger = logging.getLogger(__name__)
SEARCH_ERRORS = (EmbeddingError, ResponseHandlingException, UnexpectedResponse)


def to_sources(chunks) -> list[Citation]:
    return [
        Citation(
            label=f"S{i}",
            chunk_id=c.chunk_id,
            doc_id=c.doc_id,
            title=c.title,
            text=c.text,
            page=c.payload.get("page"),
        )
        for i, c in enumerate(chunks, start=1)
    ]


class BaselineRAG:
    def __init__(self, retriever: HybridRetriever, gateway: LLMGateway, min_relevance: float):
        self.retriever = retriever
        self.gateway = gateway
        self.min_relevance = min_relevance

    def answer(self, question: str) -> RAGAnswer:
        usage: dict = {"prompt_version": PROMPT_VERSION}
        start = time.perf_counter()
        try:
            result = self.retriever.search(question)
        except SEARCH_ERRORS as err:
            logger.exception("Retrieval failed")
            return RAGAnswer(question, "unavailable", f"Search is unavailable right now ({err}).")
        usage["retrieval_ms"] = round((time.perf_counter() - start) * 1000, 1)
        usage["retrieval_timings_ms"] = result.timings_ms

        sources = to_sources(result.chunks)
        scores = [c.ce for c in result.chunks if c.ce is not None]
        best = max(scores) if scores else None
        usage["best_relevance"] = best

        early = check_before_llm(len(sources), best, self.min_relevance)
        if early:
            return RAGAnswer(
                question, early.status, "I cannot answer this from the documents.",
                retrieved=sources, refusal_reason=early.refusal_reason, usage=usage,
            )  # fmt: skip

        messages = [
            {
                "role": "system",
                "content": ANSWER_SYSTEM.format(
                    sources=format_sources([(s.label, s.title, s.text) for s in sources])
                ),
            },  # fmt: skip
            {"role": "user", "content": question},
        ]
        try:
            llm = self.gateway.invoke("answer", messages, schema=LLMAnswer)
        except LLMError as err:
            logger.warning("LLM failed: %s", err)
            return RAGAnswer(
                question, "unavailable", "The language model is unavailable right now. "
                "Please try again later.", retrieved=sources, usage=usage,
            )  # fmt: skip
        usage |= {
            "model": llm.model,
            "input_tokens": llm.input_tokens,
            "output_tokens": llm.output_tokens,
            "cost_usd": llm.cost_usd,
            "llm_ms": llm.latency_ms,
            "cached": llm.cached,
            "llm_calls": 1,
            "llm_calls_uncached": 0 if llm.cached else 1,
            "fell_back": llm.fell_back,
        }

        out: LLMAnswer = llm.parsed
        report = verify_citations(out.claims, {s.label for s in sources})
        decision = decide_after_llm(
            out.status, len(report.valid_labels), report.invalid_labels, report.uncited_claims
        )
        by_label = {s.label: s for s in sources}
        refused_by_code = (
            decision.status == "insufficient_evidence" and out.status != decision.status
        )
        return RAGAnswer(
            question=question,
            status=decision.status,
            # If code overrules the model, do not show the unsupported answer.
            answer="I cannot answer this from the documents." if refused_by_code else out.answer,
            claims=report.claims,
            citations=[by_label[label] for label in report.valid_labels],
            retrieved=sources,
            warnings=decision.warnings,
            refusal_reason=decision.refusal_reason,
            usage=usage,
        )
