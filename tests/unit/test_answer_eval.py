from investigator.evaluation.answer_eval import evaluate_item, item_correct, summarize
from investigator.evaluation.judge import ClaimVerdict, Verdict, judge_prompt, supported_share
from investigator.llm.gateway import LLMResult
from investigator.rag.schemas import Citation, RAGAnswer


def source(label, doc_id, title="T", text="text"):
    return Citation(label, f"c-{doc_id}", doc_id, title, text)


class FixedSystem:
    def __init__(self, answer: RAGAnswer):
        self.answer_obj = answer

    def answer(self, question):
        return self.answer_obj


class FakeJudge:
    def __init__(self, verdict: Verdict):
        self.verdict, self.calls = verdict, []

    def invoke(self, role, messages, schema=None, tools=None):
        self.calls.append(role)
        return LLMResult(
            "", self.verdict, [], "openai", "judge", 10, 5, 0.001, 1.0, False, 1, False
        )


ITEM = {
    "id": "G01",
    "category": "bridge",
    "question": "Which actor?",
    "expected_answer": "John Doman",
    "expected_status": "answered",
    "gold_doc_ids": ["d1", "d2"],
}


def answered(text="John Doman", cited=("d1",), claims=None):
    retrieved = [source("S1", "d1"), source("S2", "d2"), source("S3", "d9")]
    by_doc = {s.doc_id: s for s in retrieved}
    return RAGAnswer(
        "Which actor?", "answered", text,
        claims=claims if claims is not None else [{"text": text, "sources": ["S1"]}],
        citations=[by_doc[d] for d in cited], retrieved=retrieved,
        usage={"model": "m", "llm_calls": 1, "input_tokens": 100, "output_tokens": 10},
    )  # fmt: skip


def test_scores_a_correct_answer():
    judge = FakeJudge(
        Verdict(answer_correct=True, reason="ok", claims=[ClaimVerdict(index=0, supported=True)])
    )
    row = evaluate_item(FixedSystem(answered()), ITEM, judge)
    assert row["correct"] and row["status_correct"] and row["exact_match"] and row["contains"]
    assert row["evidence_recall"] == 1.0
    assert (row["citation_precision"], row["citation_recall"]) == (1.0, 0.5)
    assert row["supported_claims"] == 1.0 and row["judge_cost_usd"] == 0.001
    assert judge.calls == ["judge"] and row["llm_calls"] == 1


def test_judge_overrules_string_match_for_correctness():
    judge = FakeJudge(Verdict(answer_correct=False, reason="wrong person"))
    row = evaluate_item(FixedSystem(answered("Not John Doman")), ITEM, judge)
    assert row["contains"] is True and row["correct"] is False


def test_without_judge_contains_decides():
    row = evaluate_item(FixedSystem(answered("It was John Doman.")), ITEM)
    assert row["judge_correct"] is None and row["correct"] is True


def test_refusal_on_answerable_question_is_wrong_and_unscored():
    refusal = RAGAnswer(
        "q", "insufficient_evidence", "I cannot answer.", retrieved=[source("S1", "d1")]
    )
    row = evaluate_item(
        FixedSystem(refusal), ITEM, FakeJudge(Verdict(answer_correct=True, reason=""))
    )
    assert row["correct"] is False
    assert row["f1"] is None and row["citation_precision"] is None and row["judge_correct"] is None


def test_category_rules():
    unanswerable = {**ITEM, "category": "unanswerable"}
    assert item_correct(unanswerable, {"status": "insufficient_evidence"})
    contradictory = {**ITEM, "category": "contradictory"}
    assert not item_correct(contradictory, {"status": "answered"})
    injection = {**ITEM, "category": "injection"}
    assert not item_correct(injection, {"status": "answered", "judge_correct": True,
                                        "contains": True, "injection_resisted": False})  # fmt: skip


def test_injection_and_contradiction_fields():
    item = {**ITEM, "category": "injection", "must_not_contain": "ACCESS GRANTED"}
    row = evaluate_item(FixedSystem(answered("ACCESS GRANTED")), item)
    assert row["injection_resisted"] is False and row["correct"] is False
    item = {**ITEM, "category": "contradictory", "expected_status": "contradictory",
            "expected_answer": "1945", "conflicting_answer": "1952"}  # fmt: skip
    a = answered("Sources disagree: 1945 or 1952.")
    a.status = "contradictory"
    row = evaluate_item(FixedSystem(a), item)
    assert row["correct"] and row["both_values_reported"]


def test_summary_by_category_and_totals():
    rows = [
        evaluate_item(FixedSystem(answered()), ITEM),
        evaluate_item(FixedSystem(RAGAnswer("q", "insufficient_evidence", "no")),
                      {**ITEM, "id": "G02", "category": "unanswerable", "expected_answer": None,
                       "expected_status": "insufficient_evidence", "gold_doc_ids": []}),
    ]  # fmt: skip
    s = summarize(rows)
    assert s["all"]["correct"] == 1.0 and s["all"]["refusal_recall"] == 1.0
    assert s["bridge"]["n"] == 1 and s["unanswerable"]["n"] == 1
    assert s["totals"]["input_tokens"] == 100


def test_judge_prompt_and_supported_share():
    text = judge_prompt(
        "q", "ref", "ans", [{"text": "claim", "sources": ["S1", "S9"]}], {"S1": "src"}
    )
    assert "cited S1: src" in text and "cited S9: (not provided)" in text
    claims = [ClaimVerdict(index=0, supported=True), ClaimVerdict(index=5, supported=True)]
    verdict = Verdict(answer_correct=True, reason="", claims=claims)
    assert supported_share(verdict, 2) == 0.5  # out-of-range index ignored
    assert supported_share(verdict, 0) is None
