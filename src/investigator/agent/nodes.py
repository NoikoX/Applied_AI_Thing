"""The agent's steps. Each is a plain function (state, deps) -> dict of changed keys.

The LLM does language work (plan, choose searches, grade, extract claims,
write the answer). Decisions that must be reliable are code: when to stop
searching, which claims conflict, whether citations are real, whether to refuse.
Every LLM failure degrades to a simpler behaviour instead of crashing.
"""

import logging
from dataclasses import dataclass

from investigator.agent.contradiction import find_conflicts, merge_evidence
from investigator.agent.prompts import (
    AGENT_PROMPT_VERSION,
    CONFLICT_NOTE,
    EXTRACT_SYSTEM,
    GRADE_SYSTEM,
    PLAN_SYSTEM,
    RETRIEVE_SYSTEM,
)
from investigator.agent.schemas import ClaimList, Grade, Plan, search_documents
from investigator.agent.state import AgentState
from investigator.config import AgentConfig
from investigator.llm.errors import LLMError
from investigator.llm.gateway import LLMGateway, LLMResult
from investigator.rag.baseline import SEARCH_ERRORS, to_sources
from investigator.rag.citations import verify_citations
from investigator.rag.prompts import ANSWER_SYSTEM, PROMPT_VERSION, format_sources
from investigator.rag.schemas import LLMAnswer, RAGAnswer
from investigator.rag.sufficiency import check_before_llm, decide_after_llm
from investigator.retrieval.search import HybridRetriever

logger = logging.getLogger(__name__)


@dataclass
class Deps:
    gateway: LLMGateway
    retriever: HybridRetriever
    cfg: AgentConfig
    min_relevance: float


def _llm_record(step: str, r: LLMResult) -> dict:
    return {"step": step, "model": r.model, "input_tokens": r.input_tokens,
            "output_tokens": r.output_tokens, "cost_usd": r.cost_usd,
            "latency_ms": r.latency_ms, "cached": r.cached, "fell_back": r.fell_back}  # fmt: skip


def _add(state: AgentState, key: str, *items) -> list:
    return [*state.get(key, []), *items]


def _sources_block(state: AgentState, deps: Deps):
    """Merged evidence as labelled sources, plus the prompt text for them."""
    sources = to_sources(merge_evidence(state.get("evidence", []), deps.cfg.max_sources))
    return sources, format_sources([(s.label, s.title, s.text) for s in sources])


# ---- nodes -------------------------------------------------------------------


def plan_node(state: AgentState, deps: Deps) -> dict:
    question = state["question"]
    calls = []
    try:
        r = deps.gateway.invoke(
            "planner",
            [{"role": "system", "content": PLAN_SYSTEM}, {"role": "user", "content": question}],
            schema=Plan,
        )
        plan, calls, note = r.parsed, [_llm_record("plan", r)], None
    except LLMError as err:
        plan, note = (
            Plan(question_type="single", sub_questions=[question]),
            f"planner failed: {err}",
        )
    plan.sub_questions = plan.sub_questions[: deps.cfg.max_queries_per_hop] or [question]
    return {
        "plan": plan, "hop": 0, "queries": [], "evidence": [],
        "trace": _add(state, "trace", {"step": "plan", "type": plan.question_type,
                                       "sub_questions": plan.sub_questions, "note": note}),
        "llm_calls": _add(state, "llm_calls", *calls),
    }  # fmt: skip


def retrieve_node(state: AgentState, deps: Deps) -> dict:
    """The LLM chooses searches by calling the search_documents tool; code runs them.

    All of a hop's queries go into ONE coverage-aware search (M5): the question is the
    main query and the tool calls are its sub-queries, so the selection step can reward
    a passage for covering a sub-query that nothing else covers yet.
    """
    hop = state.get("hop", 0) + 1
    plan, grade = state["plan"], state.get("grade")
    suggested = plan.sub_questions if hop == 1 else (grade.follow_up_queries if grade else [])
    found = [c for chunks in state.get("evidence", []) for c in chunks][:8]

    context = [f"Question: {state['question']}", "Sub-questions: " + "; ".join(plan.sub_questions)]
    if grade and grade.missing:
        context.append(f"Still missing: {grade.missing}")
    if found:
        context.append("Found so far:\n" + "\n".join(f"- {c.title}: {c.text[:160]}" for c in found))
    context.append("Suggested searches: " + "; ".join(suggested))

    calls, note = [], None
    try:
        r = deps.gateway.invoke(
            "planner",
            [{"role": "system", "content": RETRIEVE_SYSTEM.format(
                max_queries=deps.cfg.max_queries_per_hop)},
             {"role": "user", "content": "\n\n".join(context)}],
            tools=[search_documents],
        )  # fmt: skip
        calls = [_llm_record(f"retrieve-{hop}", r)]
        queries = [
            t["args"].get("query", "") for t in r.tool_calls if t["name"] == "search_documents"
        ]
    except LLMError as err:
        queries, note = [], f"tool-choosing step failed: {err}"
    if not any(q.strip() for q in queries):
        note = note or "model made no tool call; used the suggested searches"
        queries = suggested

    already = {q.lower() for qs in state.get("queries", []) for q in qs}
    queries = [
        q for q in dict.fromkeys(q.strip() for q in queries) if q and q.lower() not in already
    ]
    queries = queries[: deps.cfg.max_queries_per_hop] or [state["question"]]

    try:
        result = deps.retriever.search(state["question"], subqueries=queries)
        chunks, timings = result.chunks, result.timings_ms
    except SEARCH_ERRORS as err:
        logger.exception("Search failed in hop %s", hop)
        chunks, timings, note = [], {}, f"search failed: {err}"
    return {
        "hop": hop,
        "queries": _add(state, "queries", queries),
        "evidence": _add(state, "evidence", chunks),
        "trace": _add(state, "trace", {"step": f"retrieve-{hop}", "queries": queries,
                                       "found": [c.title for c in chunks],
                                       "timings_ms": timings, "note": note}),
        "llm_calls": _add(state, "llm_calls", *calls),
    }  # fmt: skip


def grade_node(state: AgentState, deps: Deps) -> dict:
    _, block = _sources_block(state, deps)
    calls, note = [], None
    try:
        r = deps.gateway.invoke(
            "grader",
            [{"role": "system", "content": GRADE_SYSTEM.format(
                sources=block, max_queries=deps.cfg.max_queries_per_hop)},
             {"role": "user", "content": f"Question: {state['question']}\nSub-questions: "
                                         + "; ".join(state["plan"].sub_questions)}],
            schema=Grade,
        )  # fmt: skip
        grade, calls = r.parsed, [_llm_record(f"grade-{state['hop']}", r)]
    except LLMError as err:  # without a grade, stop searching and let the answer step decide
        grade, note = Grade(sufficient=True, missing=""), f"grader failed: {err}"
    step = {
        "step": f"grade-{state['hop']}",
        "sufficient": grade.sufficient,
        "missing": grade.missing,
        "follow_up": grade.follow_up_queries,
        "note": note,
    }
    return {
        "grade": grade,
        "trace": _add(state, "trace", step),
        "llm_calls": _add(state, "llm_calls", *calls),
    }


def route_after_grade(state: AgentState, deps: Deps) -> str:
    """Code, not the LLM, decides whether to search again: only if the grader found a gap,
    proposed a search for it, and the hop budget is not used up."""
    grade = state["grade"]
    if not grade.sufficient and grade.follow_up_queries and state["hop"] < deps.cfg.max_hops:
        return "retrieve"
    return "extract"


def extract_node(state: AgentState, deps: Deps) -> dict:
    sources, block = _sources_block(state, deps)
    shown = {s.label for s in sources}
    calls, note, claims = [], None, []
    try:
        r = deps.gateway.invoke(
            "grader",
            [{"role": "system", "content": EXTRACT_SYSTEM.format(sources=block)},
             {"role": "user", "content": state["question"]}],
            schema=ClaimList,
        )  # fmt: skip
        calls = [_llm_record("extract", r)]
        claims = [c.model_dump() for c in r.parsed.claims if c.source.strip("[]") in shown]
        for c in claims:
            c["source"] = c["source"].strip("[]")
    except LLMError as err:
        note = f"claim extraction failed, contradiction check skipped: {err}"
    conflicts = find_conflicts(claims)
    return {
        "claims": claims,
        "conflicts": conflicts,
        "trace": _add(state, "trace", {"step": "extract", "n_claims": len(claims),
                                       "conflicts": conflicts, "note": note}),
        "llm_calls": _add(state, "llm_calls", *calls),
    }  # fmt: skip


def answer_node(state: AgentState, deps: Deps) -> dict:
    """Write the answer, then verify it in code (citations, refusal, contradiction)."""
    question = state["question"]
    sources, block = _sources_block(state, deps)
    scores = [c.ce for chunks in state.get("evidence", []) for c in chunks if c.ce is not None]
    best = max(scores) if scores else None
    usage = {"prompt_version": f"{PROMPT_VERSION}+{AGENT_PROMPT_VERSION}", "best_relevance": best,
             "hops": state.get("hop", 0), "queries": state.get("queries", [])}  # fmt: skip

    early = check_before_llm(len(sources), best, deps.min_relevance)
    if early:
        result = RAGAnswer(question, early.status, "I cannot answer this from the documents.",
                           retrieved=sources, refusal_reason=early.refusal_reason)  # fmt: skip
        return _finish(state, result, usage, [], "refused before the answer step")

    system = ANSWER_SYSTEM.format(sources=block)
    conflicts = state.get("conflicts", [])
    if conflicts:
        system += CONFLICT_NOTE.format(conflicts="\n".join(
            f"- {c['subject']} / {c['attribute']}: {c['values']}" for c in conflicts))  # fmt: skip
    try:
        r = deps.gateway.invoke(
            "answer",
            [{"role": "system", "content": system}, {"role": "user", "content": question}],
            schema=LLMAnswer,
        )
    except LLMError as err:
        result = RAGAnswer(question, "unavailable", "The language model is unavailable right now. "
                           "Please try again later.", retrieved=sources)  # fmt: skip
        return _finish(state, result, usage, [], f"answer step failed: {err}")

    out: LLMAnswer = r.parsed
    report = verify_citations(out.claims, {s.label for s in sources})
    decision = decide_after_llm(
        out.status, len(report.valid_labels), report.invalid_labels, report.uncited_claims
    )
    status, warnings = decision.status, list(decision.warnings)
    cited = set(report.valid_labels)
    on_cited = [c for c in conflicts if cited & {s for srcs in c["values"].values() for s in srcs}]
    if status == "answered" and on_cited:
        status = "contradictory"
        warnings.append(f"Claim check found sources disagreeing: {on_cited}")
    elif status == "contradictory" and not conflicts:
        warnings.append("The model reported a contradiction that the claim check did not find.")
    if on_cited:  # who flagged the contradiction, for the evaluation
        source = "claims+model" if out.status == "contradictory" else "claims"
    elif status == "contradictory":
        source = "model"
    else:
        source = None
    usage["contradiction_source"] = source

    refused_by_code = status == "insufficient_evidence" and out.status != status
    by_label = {s.label: s for s in sources}
    result = RAGAnswer(
        question=question,
        status=status,
        answer="I cannot answer this from the documents." if refused_by_code else out.answer,
        claims=report.claims,
        citations=[by_label[label] for label in report.valid_labels],
        retrieved=sources,
        warnings=warnings,
        refusal_reason=decision.refusal_reason,
    )
    return _finish(state, result, usage, [_llm_record("answer", r)], None)


def _finish(state: AgentState, result: RAGAnswer, usage: dict, calls: list, note) -> dict:
    llm_calls = _add(state, "llm_calls", *calls)
    trace = _add(state, "trace", {"step": "answer", "status": result.status, "note": note})
    result.usage = usage | {
        "llm_calls": len([c for c in llm_calls if not c["cached"]]),
        "input_tokens": sum(c["input_tokens"] for c in llm_calls),
        "output_tokens": sum(c["output_tokens"] for c in llm_calls),
        "cost_usd": sum(c["cost_usd"] or 0.0 for c in llm_calls),
        "llm_ms": round(sum(c["latency_ms"] for c in llm_calls), 1),
        "fell_back": any(c["fell_back"] for c in llm_calls),
        "trace": trace,
        "llm_call_log": llm_calls,
    }
    return {"result": result, "trace": trace, "llm_calls": llm_calls}
