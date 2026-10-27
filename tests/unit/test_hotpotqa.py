import pytest

from investigator.data.hotpotqa import build, sample_indices, sha256_file, write_jsonl


def record(qid, paragraphs, facts):
    """Build a record in the Hugging Face HotpotQA schema.

    paragraphs: list of (title, [sentences]); facts: list of (title, sent_id).
    """
    return {
        "id": qid,
        "question": f"question {qid}?",
        "answer": f"answer {qid}",
        "type": "bridge",
        "level": "hard",
        "context": {
            "title": [t for t, _ in paragraphs],
            "sentences": [s for _, s in paragraphs],
        },
        "supporting_facts": {
            "title": [t for t, _ in facts],
            "sent_id": [i for _, i in facts],
        },
    }


SHARED = ("Paris", ["Paris is the capital of France.", " It is on the Seine."])

RECORDS = [
    record("q1", [SHARED, ("Seine", ["The Seine is a river."])], [("Paris", 1), ("Seine", 0)]),
    # Same Paris paragraph, with different whitespace: must be deduplicated.
    record(
        "q2",
        [
            ("Paris", ["Paris is the capital  of France.", "It is on the Seine."]),
            ("Lyon", ["A city."]),
        ],
        [("Paris", 0), ("Lyon", 0)],
    ),
    record("q3", [("Rome", ["Rome is in Italy."]), ("Tiber", ["A river."])], [("Rome", 0)]),
]


def test_sample_indices_is_deterministic_and_distinct():
    a = sample_indices(1000, 50, seed=42)
    assert a == sample_indices(1000, 50, seed=42)
    assert a != sample_indices(1000, 50, seed=43)
    assert len(set(a)) == 50


def test_duplicate_paragraphs_stored_once():
    result = build(RECORDS, dev_fraction=0.5)
    paris = [d for d in result.corpus if d["title"] == "Paris"]
    assert len(paris) == 1
    assert paris[0]["question_ids"] == ["q1", "q2"]
    assert result.stats["n_paragraphs_seen"] == 6
    assert result.stats["n_unique_docs"] == 5
    assert result.stats["n_duplicates_removed"] == 1


def test_gold_points_to_corpus_docs_with_matching_titles():
    result = build(RECORDS, dev_fraction=0.5)
    by_id = {d["doc_id"]: d for d in result.corpus}
    for q in result.gold:
        assert [by_id[d]["title"] for d in q["gold_doc_ids"]] == q["gold_titles"]
        for fact in q["supporting_facts"]:
            assert fact["sent_id"] < len(by_id[fact["doc_id"]]["sentences"])


def test_sentences_are_stripped_and_joined():
    doc = next(d for d in build(RECORDS, 0.5).corpus if d["title"] == "Paris")
    assert doc["sentences"][1] == "It is on the Seine."
    assert doc["text"] == "Paris is the capital of France. It is on the Seine."


def test_dev_test_split_follows_sampled_order():
    splits = [q["split"] for q in build(RECORDS, dev_fraction=0.34).gold]
    assert splits == ["dev", "test", "test"]


def test_out_of_range_supporting_fact_is_dropped_and_counted():
    bad = record("q9", [("X", ["one sentence"])], [("X", 0), ("X", 5)])
    result = build([bad], dev_fraction=0.0)
    assert result.gold[0]["supporting_facts"] == [
        {"doc_id": result.corpus[0]["doc_id"], "title": "X", "sent_id": 0}
    ]
    assert result.stats["n_invalid_supporting_facts_dropped"] == 1


def test_gold_title_missing_from_context_raises():
    bad = record("q9", [("X", ["s"])], [("Y", 0)])
    with pytest.raises(ValueError, match="q9"):
        build([bad], dev_fraction=0.0)


def test_rebuild_produces_identical_files(tmp_path):
    hashes = []
    for name in ("a.jsonl", "b.jsonl"):
        write_jsonl(tmp_path / name, build(RECORDS, 0.5).corpus)
        hashes.append(sha256_file(tmp_path / name))
    assert hashes[0] == hashes[1]
