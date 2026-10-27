"""Turn sampled HotpotQA records into a deduplicated corpus and a gold file.

Input records use the Hugging Face schema:
    context          = {"title": [...], "sentences": [[...], ...]}
    supporting_facts = {"title": [...], "sent_id": [...]}

The corpus goes into the search index. The gold file holds the answers and
the correct paragraphs and is used only for grading, never indexed.
"""

import hashlib
import json
import random
from dataclasses import dataclass, field
from pathlib import Path

from investigator.ingestion.dedup import content_hash


@dataclass
class BuildResult:
    corpus: list[dict]
    gold: list[dict]
    stats: dict = field(default_factory=dict)


def sample_indices(n_total: int, n: int, seed: int) -> list[int]:
    """n distinct indices in random order; the same seed always gives the same list."""
    return random.Random(seed).sample(range(n_total), n)


def doc_id_for(title: str, text: str) -> str:
    """Content-addressed ID: identical paragraphs get the same ID in every build."""
    return "hp_" + content_hash(title, text)[:16]


def build(records: list[dict], dev_fraction: float) -> BuildResult:
    """Deduplicate paragraphs and link each question to its gold paragraphs.

    Records must already be in sampled order: the first `dev_fraction` of them
    become the dev split (for tuning), the rest the test split (for reporting).
    """
    docs: dict[str, dict] = {}
    gold: list[dict] = []
    n_paragraphs = 0
    n_invalid_facts = 0
    n_dev = round(len(records) * dev_fraction)

    for i, rec in enumerate(records):
        title_to_doc: dict[str, dict] = {}
        for title, sentences in zip(
            rec["context"]["title"], rec["context"]["sentences"], strict=True
        ):
            n_paragraphs += 1
            sentences = [s.strip() for s in sentences]
            text = " ".join(sentences)
            doc_id = doc_id_for(title, text)
            if doc_id not in docs:
                docs[doc_id] = {
                    "doc_id": doc_id,
                    "title": title,
                    "text": text,
                    "sentences": sentences,
                    "source": "hotpotqa",
                    "question_ids": [],
                }
            docs[doc_id]["question_ids"].append(rec["id"])
            title_to_doc[title] = docs[doc_id]

        gold_titles = list(dict.fromkeys(rec["supporting_facts"]["title"]))
        missing = [t for t in gold_titles if t not in title_to_doc]
        if missing:
            raise ValueError(f"Question {rec['id']}: gold titles not in context: {missing}")

        facts = []
        for title, sent_id in zip(
            rec["supporting_facts"]["title"], rec["supporting_facts"]["sent_id"], strict=True
        ):
            doc = title_to_doc[title]
            if 0 <= sent_id < len(doc["sentences"]):
                facts.append({"doc_id": doc["doc_id"], "title": title, "sent_id": sent_id})
            else:
                n_invalid_facts += 1  # known HotpotQA label noise

        gold.append(
            {
                "id": rec["id"],
                "question": rec["question"],
                "answer": rec["answer"],
                "type": rec["type"],
                "level": rec["level"],
                "gold_titles": gold_titles,
                "gold_doc_ids": [title_to_doc[t]["doc_id"] for t in gold_titles],
                "supporting_facts": facts,
                "split": "dev" if i < n_dev else "test",
            }
        )

    stats = {
        "n_questions": len(gold),
        "n_dev": n_dev,
        "n_test": len(gold) - n_dev,
        "n_paragraphs_seen": n_paragraphs,
        "n_unique_docs": len(docs),
        "n_duplicates_removed": n_paragraphs - len(docs),
        "n_invalid_supporting_facts_dropped": n_invalid_facts,
    }
    return BuildResult(corpus=list(docs.values()), gold=gold, stats=stats)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    # newline="\n" keeps files byte-identical (and hashes equal) on Windows and Linux.
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
