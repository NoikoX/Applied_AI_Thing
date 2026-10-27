"""Citation verification (hand-written).

The model cites short labels ("S3") instead of chunk IDs: labels are easy to
copy correctly, and a label that was never shown is detectable. This module
checks every cited label against the sources actually given to the model.
"""

from dataclasses import dataclass, field

from investigator.rag.schemas import Claim


@dataclass
class CitationReport:
    valid_labels: list[str]  # cited and shown, in first-cited order
    invalid_labels: list[str]  # cited but never shown: a fabricated source
    uncited_claims: list[str]  # claims left with no valid source
    claims: list[dict] = field(default_factory=list)  # claims with only valid sources kept


def verify_citations(claims: list[Claim], shown_labels: set[str]) -> CitationReport:
    valid: list[str] = []
    invalid: list[str] = []
    uncited: list[str] = []
    cleaned: list[dict] = []
    for claim in claims:
        sources = [s.strip().strip("[]") for s in claim.sources]  # tolerate "[S1]"
        good = [s for s in sources if s in shown_labels]
        for s in sources:
            target = valid if s in shown_labels else invalid
            if s not in target:
                target.append(s)
        if not good:
            uncited.append(claim.text)
        cleaned.append({"text": claim.text, "sources": list(dict.fromkeys(good))})
    return CitationReport(valid, invalid, uncited, cleaned)
