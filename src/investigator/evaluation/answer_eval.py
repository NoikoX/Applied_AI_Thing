"""Run a QA system (baseline or agent) over golden questions and score every answer."""

import time

from investigator.evaluation.answer_metrics import (
    citation_precision,
    citation_recall,
    contains_answer,
    exact_match,
    refusal_scores,
    token_f1,
)
from investigator.evaluation.judge import judge, supported_share
from investigator.llm.errors import LLMError

ANSWERING = {"answered", "contradictory"}


def item_correct(item: dict, row: dict) -> bool:
    """The one headline yes/no per question, by category."""
    category = item["category"]
    if category == "unanswerable":
        return row["status"] == "insufficient_evidence"
    if category == "contradictory":
        return row["status"] == "contradictory"
    answered_right = row["judge_correct"] if row["judge_correct"] is not None else row["contains"]
    if category == "injection":
        return bool(answered_right) and row["injection_resisted"]
    return bool(answered_right) and row["status"] == "answered"


def evaluate_item(system, item: dict, gateway=None) -> dict:
    """gateway: for the LLM judge; None skips judging (offline tests)."""
    start = time.perf_counter()
    a = system.answer(item["question"])
    latency_ms = round((time.perf_counter() - start) * 1000, 1)

    expected = item["expected_answer"]
    gold = item["gold_doc_ids"]
    cited = [c.doc_id for c in a.citations]
    retrieved = [s.doc_id for s in a.retrieved]
    gives_answer = a.status in ANSWERING and expected is not None
    row = {
        "id": item["id"],
        "category": item["category"],
        "question": item["question"],
        "expected_status": item["expected_status"],
        "status": a.status,
        "status_correct": a.status == item["expected_status"],
        "answer": a.answer,
        "expected_answer": expected,
        "exact_match": exact_match(a.answer, expected) if gives_answer else None,
        "f1": token_f1(a.answer, expected) if gives_answer else None,
        "contains": contains_answer(a.answer, expected) if gives_answer else None,
        "evidence_recall": len(set(retrieved) & set(gold)) / len(gold) if gold else None,
        "citation_precision": citation_precision(cited, gold) if a.status in ANSWERING else None,
        "citation_recall": citation_recall(cited, gold) if a.status in ANSWERING else None,
        "injection_resisted": (
            item["must_not_contain"].lower() not in a.answer.lower()
            if item.get("must_not_contain") else None
        ),
        "judge_correct": None,
        "supported_claims": None,
        "cited_titles": [c.title for c in a.citations],
        "retrieved_titles": [s.title for s in a.retrieved],
        "warnings": a.warnings,
        "refusal_reason": a.refusal_reason,
    }  # fmt: skip
    if item["category"] == "contradictory":
        row["both_values_reported"] = contains_answer(a.answer, expected) and contains_answer(
            a.answer, item["conflicting_answer"]
        )

    judge_usage = {}
    if gateway is not None and a.status in ANSWERING and a.claims:
        reference = expected or "(none: the question should have been refused)"
        if item.get("conflicting_answer"):
            reference += f" (a second source says {item['conflicting_answer']})"
        sources = {s.label: f"{s.title}: {s.text}" for s in a.retrieved}
        try:
            verdict, judge_usage = judge(gateway, item["question"], reference, a.answer,
                                         a.claims, sources)  # fmt: skip
            row["judge_correct"] = verdict.answer_correct if expected else None
            row["judge_reason"] = verdict.reason
            row["supported_claims"] = supported_share(verdict, len(a.claims))
        except LLMError as err:
            row["judge_error"] = str(err)

    row["correct"] = item_correct(item, row)
    usage = a.usage or {}
    row |= {
        "llm_calls": usage.get("llm_calls", 1 if usage.get("model") else 0),
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "cost_usd": usage.get("cost_usd") or 0.0,
        "fell_back": usage.get("fell_back", False),
        "hops": usage.get("hops"),
        "latency_ms": latency_ms,
        "judge_cost_usd": judge_usage.get("cost_usd") or 0.0,
    }
    return row


def _mean(values):
    kept = [float(v) for v in values if v is not None]
    return round(sum(kept) / len(kept), 4) if kept else None


METRICS = ["correct", "status_correct", "exact_match", "f1", "contains", "judge_correct",
           "supported_claims", "evidence_recall", "citation_precision", "citation_recall",
           "injection_resisted", "both_values_reported", "llm_calls", "latency_ms"]  # fmt: skip


def summarize(rows: list[dict]) -> dict:
    def block(subset):
        out = {"n": len(subset)}
        out |= {m: _mean([r.get(m) for r in subset]) for m in METRICS}
        return out

    summary = {"all": block(rows) | refusal_scores(rows)}
    for category in sorted({r["category"] for r in rows}):
        summary[category] = block([r for r in rows if r["category"] == category])
    summary["totals"] = {
        "llm_calls": sum(r["llm_calls"] for r in rows),
        "input_tokens": sum(r["input_tokens"] for r in rows),
        "output_tokens": sum(r["output_tokens"] for r in rows),
        "cost_usd": round(sum(r["cost_usd"] for r in rows), 6),
        "judge_cost_usd": round(sum(r["judge_cost_usd"] for r in rows), 6),
        "answers_using_fallback": sum(bool(r["fell_back"]) for r in rows),
    }
    return summary
