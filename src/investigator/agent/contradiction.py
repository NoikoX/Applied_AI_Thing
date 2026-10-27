"""Contradiction detection and evidence merging (hand-written).

The LLM only extracts claims as (subject, attribute, value, source,
single_valued). Deciding whether two claims conflict is done here, deterministically:

  1. keep only single-valued properties: two different birth dates conflict, two
     different films an actor appeared in do not (found live in M9: "John Doman /
     actor in" = "Emmett's Mark" and "The Wire" was wrongly flagged)
  2. normalize subject, attribute and value (case, punctuation, articles, spacing)
  3. group claims by (subject, attribute)
  4. a group whose claims have different values, coming from different sources,
     is a conflict

Known limits: synonyms are not merged ("birthplace" vs "place of birth", "USA"
vs "United States"), so some real conflicts are missed and some spelling
variants could be flagged; a value whose words all appear in the other
("1945" vs "May 1945") counts as agreement: one source is just more specific.
"""

import re
from itertools import zip_longest

from investigator.retrieval.candidate import Candidate

_ARTICLES = {"the", "a", "an"}


def normalize(text: str) -> str:
    words = re.sub(r"[^\w\s]", " ", text.lower()).split()
    return " ".join(w for w in words if w not in _ARTICLES)


def _agree(a: str, b: str) -> bool:
    """Equal, or all words of one appear in the other ("1945" vs "may 1945").
    Whole words, so "1" and "10" do disagree."""
    wa, wb = set(a.split()), set(b.split())
    return wa <= wb or wb <= wa


def find_conflicts(claims: list[dict]) -> list[dict]:
    """claims: [{"subject", "attribute", "value", "source", "single_valued"}] -> conflicts."""
    groups: dict[tuple[str, str], list[dict]] = {}
    for c in claims:
        if not c.get("single_valued", True):
            continue
        key = (normalize(c["subject"]), normalize(c["attribute"]))
        if all(key) and normalize(c["value"]):
            groups.setdefault(key, []).append(c)

    conflicts = []
    for (subject, attribute), group in groups.items():
        values: dict[str, set[str]] = {}  # normalized value -> sources stating it
        for c in group:
            values.setdefault(normalize(c["value"]), set()).add(c["source"])
        distinct = list(values)
        disagreeing = {v for v in distinct for w in distinct if v != w and not _agree(v, w)}
        sources = {s for v in disagreeing for s in values[v]}
        if disagreeing and len(sources) > 1:
            conflicts.append(
                {
                    "subject": subject,
                    "attribute": attribute,
                    "values": {v: sorted(values[v]) for v in sorted(disagreeing)},
                }
            )
    return conflicts


def merge_evidence(hops: list[list[Candidate]], max_sources: int) -> list[Candidate]:
    """Interleave hops by rank (hop1 #1, hop2 #1, hop1 #2, ...), dropping repeats.

    Reranker scores from different hops were computed against different queries,
    so they are not comparable; interleaving guarantees each hop's best passages
    reach the answer step, which is the point of doing a second hop.
    """
    merged: list[Candidate] = []
    seen: set[str] = set()
    for row in zip_longest(*hops):
        for c in row:
            if c is not None and c.chunk_id not in seen:
                seen.add(c.chunk_id)
                merged.append(c)
                if len(merged) == max_sources:
                    return merged
    return merged
