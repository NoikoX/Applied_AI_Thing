"""State passed between the agent's nodes. Each node returns only the keys it changes."""

from typing import TypedDict

from investigator.agent.schemas import Grade, Plan
from investigator.rag.schemas import RAGAnswer
from investigator.retrieval.candidate import Candidate


class AgentState(TypedDict, total=False):
    question: str
    plan: Plan
    hop: int  # retrieval rounds done
    queries: list[list[str]]  # queries run in each hop
    evidence: list[list[Candidate]]  # chunks selected in each hop
    grade: Grade
    claims: list[dict]  # extracted (subject, attribute, value, source)
    conflicts: list[dict]  # found by contradiction.find_conflicts
    result: RAGAnswer
    trace: list[dict]  # one entry per step, for the UI and debugging
    llm_calls: list[dict]  # model, tokens, cost, latency of every LLM call
