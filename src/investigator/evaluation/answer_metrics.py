"""Answer-quality metrics (hand-written).

Answers are short sentences, not bare spans, so exact match is strict by design
and "contains" is the lenient version; token F1 sits in between. Semantic
correctness and grounding come from the LLM judge (judge.py) and are reported
separately, so a reader can see which numbers depend on a model.
"""

import re
import string
from collections import Counter

_ARTICLES = re.compile(r"\b(a|an|the)\b")


def normalize_answer(text: str) -> str:
    """HotpotQA/SQuAD normalization: lower case, no punctuation, no articles, single spaces."""
    text = text.lower()
    text = "".join(ch for ch in text if ch not in set(string.punctuation))
    text = _ARTICLES.sub(" ", text)
    return " ".join(text.split())


def exact_match(prediction: str, gold: str) -> bool:
    return normalize_answer(prediction) == normalize_answer(gold)


def token_f1(prediction: str, gold: str) -> float:
    pred, ref = normalize_answer(prediction).split(), normalize_answer(gold).split()
    if not pred or not ref:
        return float(pred == ref)
    common = sum((Counter(pred) & Counter(ref)).values())
    if common == 0:
        return 0.0
    precision, recall = common / len(pred), common / len(ref)
    return 2 * precision * recall / (precision + recall)


def contains_answer(prediction: str, gold: str) -> bool:
    """The normalized gold answer appears as whole words inside the prediction."""
    pred, ref = normalize_answer(prediction), normalize_answer(gold)
    return bool(ref) and re.search(rf"(?<!\w){re.escape(ref)}(?!\w)", pred) is not None


def citation_precision(cited: list[str], gold: list[str]) -> float | None:
    """Share of cited documents that are gold. None if nothing was cited."""
    cited_set = set(cited)
    return len(cited_set & set(gold)) / len(cited_set) if cited_set else None


def citation_recall(cited: list[str], gold: list[str]) -> float | None:
    """Share of gold documents that were cited. None if the question has no gold documents."""
    gold_set = set(gold)
    return len(set(cited) & gold_set) / len(gold_set) if gold_set else None


def refusal_scores(rows: list[dict]) -> dict:
    """Precision/recall of refusing, where a refusal is status insufficient_evidence.

    precision: of the questions we refused, how many should have been refused
    recall:    of the questions that should be refused, how many we refused
    """
    refused = [r for r in rows if r["status"] == "insufficient_evidence"]
    should = [r for r in rows if r["expected_status"] == "insufficient_evidence"]
    correct = [r for r in refused if r["expected_status"] == "insufficient_evidence"]
    return {
        "refusal_precision": len(correct) / len(refused) if refused else None,
        "refusal_recall": len(correct) / len(should) if should else None,
        "refused": len(refused),
        "should_refuse": len(should),
    }
