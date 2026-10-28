"""The committed golden set meets the task's requirements and is internally consistent."""

import json
from collections import Counter

import pytest

from investigator.config import PROJECT_ROOT
from investigator.ingestion.loaders import upload_doc_id

GOLDEN = PROJECT_ROOT / "eval" / "golden"
ITEMS = [
    json.loads(line) for line in (GOLDEN / "golden.jsonl").read_text(encoding="utf-8").splitlines()
]
PLAN = json.loads((GOLDEN / "index_plan.json").read_text(encoding="utf-8"))


def test_at_least_40_hand_verified_questions_with_unique_ids():
    assert len(ITEMS) >= 40
    assert all(i["verified"] for i in ITEMS)
    assert len({i["id"] for i in ITEMS}) == len(ITEMS)


def test_every_required_category_is_covered():
    counts = Counter(i["category"] for i in ITEMS)
    assert counts["simple"] >= 5
    assert counts["bridge"] + counts["comparison"] >= 10  # multi-step, linking documents
    assert counts["unanswerable"] >= 5
    assert counts["contradictory"] >= 5


@pytest.mark.parametrize("item", ITEMS, ids=[i["id"] for i in ITEMS])
def test_item_fields_match_its_category(item):
    if item["category"] == "unanswerable":
        assert (
            item["expected_answer"] is None and item["expected_status"] == "insufficient_evidence"
        )
        assert item["gold_doc_ids"] == []
        return
    assert item["expected_answer"] and item["gold_doc_ids"]
    if item["category"] == "contradictory":
        assert item["expected_status"] == "contradictory"
        assert item["conflicting_answer"] != item["expected_answer"]
    if item["category"] == "injection":
        assert item["must_not_contain"]
    if item.get("upload"):
        assert (GOLDEN / "docs" / item["upload"]).exists()
        assert upload_doc_id(item["upload"]) in item["gold_doc_ids"]
        assert item["upload"] in PLAN["uploads"]


def test_deleted_paragraphs_belong_to_unanswerable_questions_only():
    removed = set(PLAN["remove_doc_ids"])
    assert removed == {i["removed_doc_id"] for i in ITEMS if i.get("removed_doc_id")}
    for item in ITEMS:
        assert not removed & set(item["gold_doc_ids"])
