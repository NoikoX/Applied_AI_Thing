"""Structured outputs and the tool the agent's LLM steps use."""

from typing import Literal

from pydantic import BaseModel, Field


class Plan(BaseModel):
    question_type: Literal["single", "bridge", "comparison"] = Field(
        description=(
            "single: one fact. bridge: find an entity first, then a fact about it. "
            "comparison: the same property of two or more entities."
        )
    )
    sub_questions: list[str] = Field(
        description="1-3 short questions that together answer the question, in order."
    )


class search_documents(BaseModel):  # noqa: N801 - the tool name the model sees
    """Search the document collection. Call once per thing you need to look up."""

    query: str = Field(description="Short search query, e.g. an entity name plus the fact wanted.")


class Grade(BaseModel):
    sufficient: bool = Field(description="True if the sources answer every sub-question.")
    missing: str = Field(default="", description="What is still unknown, if anything.")
    follow_up_queries: list[str] = Field(
        default_factory=list,
        description=(
            "Searches that would find what is missing. Use names found in the sources, "
            "e.g. the person a source mentions, not words from the question."
        ),
    )


class ExtractedClaim(BaseModel):
    subject: str = Field(description="The entity, e.g. 'Leo Strauss'.")
    attribute: str = Field(description="The property, in 1-3 words, e.g. 'nationality'.")
    value: str = Field(description="The value as the source states it, e.g. 'German-American'.")
    source: str = Field(description="The source label, e.g. 'S3'.")
    single_valued: bool = Field(
        description=(
            "True if the property can have only one true value (birth date, nationality, "
            "founding year, release date). False if many values can all be true at once "
            "(films an actor appeared in, members of a band, awards won)."
        )
    )


class ClaimList(BaseModel):
    claims: list[ExtractedClaim] = Field(
        default_factory=list,
        description="Facts from the sources that bear on the question, one per source statement.",
    )
