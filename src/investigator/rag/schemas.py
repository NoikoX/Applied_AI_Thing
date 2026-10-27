"""Structured output the LLM must return, and the answer the system returns."""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

Status = Literal["answered", "insufficient_evidence", "contradictory"]


class Claim(BaseModel):
    text: str = Field(description="One factual statement used in the answer.")
    sources: list[str] = Field(description="Labels of the sources that state it, e.g. ['S2'].")


class LLMAnswer(BaseModel):
    """What the model returns (validated by the gateway's structured output)."""

    status: Status = Field(
        description=(
            "answered: the sources contain the answer. "
            "insufficient_evidence: they do not. "
            "contradictory: sources disagree on a fact the answer depends on."
        )
    )
    answer: str = Field(
        description="Short answer, or why it cannot be answered. No citations here."
    )
    claims: list[Claim] = Field(
        default_factory=list, description="Every fact the answer relies on, each with its sources."
    )


@dataclass
class Citation:
    label: str  # "S1".."Sk", as shown to the model
    chunk_id: str
    doc_id: str
    title: str
    text: str
    page: int | None = None


@dataclass
class RAGAnswer:
    question: str
    status: Literal["answered", "insufficient_evidence", "contradictory", "unavailable"]
    answer: str
    claims: list[dict] = field(default_factory=list)  # {"text", "sources": [labels]}
    citations: list[Citation] = field(default_factory=list)  # sources actually cited
    retrieved: list[Citation] = field(default_factory=list)  # everything shown to the model
    warnings: list[str] = field(default_factory=list)
    refusal_reason: str | None = None
    usage: dict = field(default_factory=dict)  # model, tokens, cost, latencies
