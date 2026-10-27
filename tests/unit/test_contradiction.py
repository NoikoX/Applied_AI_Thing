from investigator.agent.contradiction import find_conflicts, merge_evidence, normalize
from investigator.retrieval.candidate import Candidate


def claim(subject, attribute, value, source, single_valued=True):
    return {"subject": subject, "attribute": attribute, "value": value, "source": source,
            "single_valued": single_valued}  # fmt: skip


def test_multi_valued_properties_never_conflict():
    # Found live: an actor appearing in two works is not a contradiction.
    claims = [
        claim("John Doman", "actor in", "Emmett's Mark", "S1", single_valued=False),
        claim("John Doman", "actor in", "The Wire", "S4", single_valued=False),
    ]
    assert find_conflicts(claims) == []


def test_normalize():
    assert normalize("  The Payment-Service ") == "payment service"


def test_different_values_from_different_sources_conflict():
    conflicts = find_conflicts(
        [
            claim("Payment outage", "start date", "12 March", "S1"),
            claim("payment outage", "Start date", "14 March", "S3"),
        ]
    )
    assert conflicts == [
        {
            "subject": "payment outage",
            "attribute": "start date",
            "values": {"12 march": ["S1"], "14 march": ["S3"]},
        }
    ]


def test_more_specific_value_is_agreement():
    assert (
        find_conflicts(
            [claim("X", "founded", "1945", "S1"), claim("X", "founded", "May 1945", "S2")]
        )
        == []
    )


def test_whole_words_so_1_and_10_disagree():
    assert (
        len(find_conflicts([claim("X", "count", "1", "S1"), claim("X", "count", "10", "S2")])) == 1
    )


def test_same_source_saying_two_things_is_not_a_cross_source_conflict():
    assert (
        find_conflicts([claim("X", "colour", "red", "S1"), claim("X", "colour", "blue", "S1")])
        == []
    )


def test_different_attributes_or_subjects_do_not_conflict():
    claims = [
        claim("Leo Strauss", "nationality", "German-American", "S1"),
        claim("Leo Strauss", "profession", "philosopher", "S2"),
        claim("Harry Jaffa", "nationality", "American", "S3"),
    ]
    assert find_conflicts(claims) == []


def test_empty_fields_are_ignored():
    assert find_conflicts([claim("", "x", "1", "S1"), claim("", "x", "2", "S2")]) == []


def cands(*ids):
    return [Candidate(i, f"d{i}", i, "", {}) for i in ids]


def test_merge_interleaves_hops_dedupes_and_caps():
    hop1, hop2 = cands("a", "b", "c"), cands("x", "a", "y")
    assert [c.chunk_id for c in merge_evidence([hop1, hop2], 10)] == ["a", "x", "b", "c", "y"]
    assert [c.chunk_id for c in merge_evidence([hop1, hop2], 3)] == ["a", "x", "b"]
    assert merge_evidence([], 5) == []
