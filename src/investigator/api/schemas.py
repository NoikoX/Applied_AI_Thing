"""Request and response bodies of the REST API."""

from typing import Literal

from pydantic import BaseModel, Field

from investigator.rag.schemas import Citation, RAGAnswer


class AskIn(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    mode: Literal["agent", "baseline"] | None = None  # None: the configured default


class SourceOut(BaseModel):
    label: str
    doc_id: str
    title: str
    text: str
    page: int | None = None


class AnswerOut(BaseModel):
    question: str
    status: str
    answer: str
    claims: list[dict]
    citations: list[SourceOut]
    retrieved: list[SourceOut]
    warnings: list[str]
    refusal_reason: str | None
    usage: dict

    @classmethod
    def from_answer(cls, a: RAGAnswer) -> "AnswerOut":
        def source(c: Citation) -> SourceOut:
            return SourceOut(
                label=c.label, doc_id=c.doc_id, title=c.title, text=c.text, page=c.page
            )

        # The per-call log is for evaluation; the trace (steps, queries) stays for transparency.
        usage = {k: v for k, v in (a.usage or {}).items() if k != "llm_call_log"}
        return cls(
            question=a.question,
            status=a.status,
            answer=a.answer,
            claims=a.claims,
            citations=[source(c) for c in a.citations],
            retrieved=[source(c) for c in a.retrieved],
            warnings=a.warnings,
            refusal_reason=a.refusal_reason,
            usage=usage,
        )


class UploadOut(BaseModel):
    doc_id: str
    status: str
    n_chunks: int
    n_near_duplicates: int
    n_possible_conflicts: int
    duplicate_of: str | None


class DocumentPage(BaseModel):
    documents: list[dict]
    next_offset: str | None
