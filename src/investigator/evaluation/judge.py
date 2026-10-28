"""LLM judge: semantic correctness and claim grounding (the hallucination check).

Uses the `judge` role (an OpenAI model) while answers come from Gemini, so the
judge is not grading its own model family. It never falls back to another model,
because a different judge would change the grades. Its verdicts are reported
next to the hand-written metrics, never instead of them.
"""

from pydantic import BaseModel, Field

from investigator.llm.gateway import LLMGateway

JUDGE_PROMPT_VERSION = "judge-v1"

JUDGE_SYSTEM = """You grade a question-answering system. Be strict and literal.

1. answer_correct: does the system's answer give the reference answer (same meaning;
   extra correct detail is fine; a different or partial entity is not)?
2. For each numbered claim: is it supported by the cited source text shown under it?
   "Supported" means the source states it or directly implies it. Outside knowledge
   does not count, even if the claim is true."""


class ClaimVerdict(BaseModel):
    index: int
    supported: bool


class Verdict(BaseModel):
    answer_correct: bool
    reason: str = Field(description="One short sentence.")
    claims: list[ClaimVerdict] = Field(default_factory=list)


def judge_prompt(question: str, reference: str, answer: str, claims: list[dict],
                 sources: dict[str, str]) -> str:  # fmt: skip
    """claims: [{"text", "sources": [labels]}]; sources: label -> passage text."""
    lines = [f"Question: {question}", f"Reference answer: {reference}",
             f"System answer: {answer}", "", "Claims:"]  # fmt: skip
    for i, claim in enumerate(claims):
        lines.append(f"[{i}] {claim['text']}")
        for label in claim["sources"]:
            lines.append(f"    cited {label}: {sources.get(label, '(not provided)')}")
    if not claims:
        lines.append("(none)")
    return "\n".join(lines)


def judge(gateway: LLMGateway, question: str, reference: str, answer: str,
          claims: list[dict], sources: dict[str, str]) -> tuple[Verdict, dict]:  # fmt: skip
    """Returns the verdict and the judge call's usage (tokens, cost)."""
    r = gateway.invoke(
        "judge",
        [{"role": "system", "content": JUDGE_SYSTEM},
         {"role": "user", "content": judge_prompt(question, reference, answer, claims, sources)}],
        schema=Verdict,
    )  # fmt: skip
    usage = {"model": r.model, "input_tokens": r.input_tokens, "output_tokens": r.output_tokens,
             "cost_usd": r.cost_usd, "cached": r.cached}  # fmt: skip
    return r.parsed, usage


def supported_share(verdict: Verdict, n_claims: int) -> float | None:
    """Share of claims the judge found supported by their cited sources."""
    if n_claims == 0:
        return None
    supported = {v.index for v in verdict.claims if v.supported and 0 <= v.index < n_claims}
    return len(supported) / n_claims
