"""Refuse-or-answer decision (hand-written).

The model's own "insufficient_evidence" is one signal, but models are
over-confident, so code also refuses when the evidence is weak, whatever the
model says. Two checkpoints; the first rule that fires decides.

Before the LLM call (a refusal here also saves an LLM request):
  1. nothing retrieved                                 -> refuse
  2. best reranker score below min_relevance           -> refuse (nothing on topic was found)
After the LLM call:
  3. model says insufficient_evidence                  -> refuse
  4. model answered but cited no valid source at all   -> refuse (the answer is unsupported)
  5. otherwise keep the model's status; uncited claims and fabricated labels become warnings
"""

from dataclasses import dataclass, field


@dataclass
class Decision:
    status: str  # answered | insufficient_evidence | contradictory
    refusal_reason: str | None
    warnings: list[str] = field(default_factory=list)


def check_before_llm(
    n_retrieved: int, best_relevance: float | None, min_relevance: float
) -> Decision | None:
    """A refusal, or None to go on and ask the model."""
    if n_retrieved == 0:
        return Decision("insufficient_evidence", "No documents were retrieved.")
    if best_relevance is not None and best_relevance < min_relevance:
        return Decision(
            "insufficient_evidence",
            f"No retrieved passage is relevant enough "
            f"(best {best_relevance:.3f} < {min_relevance}).",
        )
    return None


def decide_after_llm(
    model_status: str,
    n_valid_citations: int,
    invalid_labels: list[str],
    uncited_claims: list[str],
) -> Decision:
    if model_status == "insufficient_evidence":
        return Decision("insufficient_evidence", "The sources do not contain the answer.")
    if n_valid_citations == 0:
        return Decision("insufficient_evidence", "The answer did not cite any of the sources.")

    warnings = []
    if invalid_labels:
        warnings.append(f"Ignored citations to sources that were not provided: {invalid_labels}")
    if uncited_claims:
        warnings.append(f"{len(uncited_claims)} claim(s) have no valid source: {uncited_claims}")
    return Decision(model_status, None, warnings)
