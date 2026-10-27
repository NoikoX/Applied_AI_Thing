"""Retrieval metrics (hand-written).

All metrics look at the top K *chunks* returned, because that is what the LLM
receives. A document counts as retrieved if any of its chunks is in the top K.
"""

from dataclasses import dataclass


@dataclass
class RetrievedChunk:
    doc_id: str
    sent_start: int | None = None  # None: the chunk is a whole paragraph
    sent_end: int | None = None


def recall_at_k(retrieved: list[RetrievedChunk], gold_doc_ids: list[str], k: int) -> float:
    """Share of gold documents with at least one chunk in the top k."""
    top = {c.doc_id for c in retrieved[:k]}
    return len(top & set(gold_doc_ids)) / len(gold_doc_ids)


def full_support_at_k(retrieved: list[RetrievedChunk], gold_doc_ids: list[str], k: int) -> bool:
    """All gold documents in the top k: what a multi-hop answer actually needs."""
    return set(gold_doc_ids) <= {c.doc_id for c in retrieved[:k]}


def reciprocal_rank(retrieved: list[RetrievedChunk], gold_doc_ids: list[str]) -> float:
    """1 / position of the first chunk from a gold document; 0 if none was retrieved."""
    gold = set(gold_doc_ids)
    for position, chunk in enumerate(retrieved, start=1):
        if chunk.doc_id in gold:
            return 1.0 / position
    return 0.0


def _covers(chunk: RetrievedChunk, doc_id: str, sent_id: int) -> bool:
    if chunk.doc_id != doc_id:
        return False
    if chunk.sent_start is None:  # paragraph chunk: contains every sentence of the document
        return True
    return chunk.sent_start <= sent_id < chunk.sent_end


def sentence_recall_at_k(
    retrieved: list[RetrievedChunk], supporting_facts: list[tuple[str, int]], k: int
) -> float | None:
    """Share of supporting sentences (doc_id, sentence index) inside the top k chunks.

    None when a question has no supporting-sentence labels, so it is left out of
    the average instead of counting as 0.
    """
    if not supporting_facts:
        return None
    top = retrieved[:k]
    found = sum(any(_covers(c, d, s) for c in top) for d, s in supporting_facts)
    return found / len(supporting_facts)


def mean(values: list[float | bool | None]) -> float | None:
    """Average that skips None; None if nothing is left."""
    kept = [float(v) for v in values if v is not None]
    return sum(kept) / len(kept) if kept else None
