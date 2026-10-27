import pytest

from investigator.index.embeddings import EmbeddingError
from investigator.llm.errors import LLMQuotaExceeded
from investigator.llm.gateway import LLMResult
from investigator.rag.baseline import BaselineRAG
from investigator.rag.citations import verify_citations
from investigator.rag.prompts import PROMPT_VERSION
from investigator.rag.schemas import Claim, LLMAnswer
from investigator.rag.sufficiency import check_before_llm, decide_after_llm
from investigator.retrieval.candidate import Candidate
from investigator.retrieval.search import RetrievalResult

# ---- citation verification ------------------------------------------------


def test_valid_and_fabricated_labels_are_separated():
    claims = [
        Claim(text="John Doman starred in Emmett's Mark.", sources=["S1", "[S2]"]),
        Claim(text="He played Rawls in The Wire.", sources=["S9"]),  # S9 was never shown
    ]
    report = verify_citations(claims, {"S1", "S2", "S3"})
    assert report.valid_labels == ["S1", "S2"]
    assert report.invalid_labels == ["S9"]
    assert report.uncited_claims == ["He played Rawls in The Wire."]
    assert report.claims[1]["sources"] == []


def test_repeated_labels_are_listed_once():
    claims = [Claim(text="a", sources=["S2", "S2"]), Claim(text="b", sources=["S2", "S1"])]
    report = verify_citations(claims, {"S1", "S2"})
    assert report.valid_labels == ["S2", "S1"]
    assert report.claims[0]["sources"] == ["S2"]


# ---- refusal rules ---------------------------------------------------------


def test_refuse_before_llm_when_nothing_or_nothing_relevant():
    assert check_before_llm(0, None, 0.05).status == "insufficient_evidence"
    assert "relevant enough" in check_before_llm(5, 0.01, 0.05).refusal_reason
    assert check_before_llm(5, 0.9, 0.05) is None
    assert check_before_llm(5, None, 0.05) is None  # no reranker: no score to judge by


def test_refuse_after_llm():
    assert decide_after_llm("insufficient_evidence", 2, [], []).status == "insufficient_evidence"
    unsupported = decide_after_llm("answered", 0, ["S9"], ["x"])
    assert unsupported.status == "insufficient_evidence"
    assert "did not cite" in unsupported.refusal_reason


def test_answer_with_problems_is_kept_but_warned():
    d = decide_after_llm("answered", 1, ["S9"], ["an uncited claim"])
    assert d.status == "answered" and d.refusal_reason is None
    assert len(d.warnings) == 2


def test_contradictory_status_is_kept():
    assert decide_after_llm("contradictory", 2, [], []).status == "contradictory"


# ---- pipeline ----------------------------------------------------------------


def chunk(i: int, title: str, text: str, ce: float | None = 0.9) -> Candidate:
    return Candidate(f"c{i}", f"hp_{i}", title, text, {"page": None}, ce=ce)


CHUNKS = [
    chunk(1, "Emmett's Mark", "Emmett's Mark is a 2002 film starring John Doman."),
    chunk(2, "John Doman", "John Doman played William Rawls in The Wire.", ce=0.7),
]


class FakeRetriever:
    def __init__(self, chunks=CHUNKS, error=None):
        self.chunks, self.error = chunks, error

    def search(self, question):
        if self.error:
            raise self.error
        return RetrievalResult(list(self.chunks), False, len(self.chunks), {"embed": 1.0})


class FakeGateway:
    def __init__(self, answer: LLMAnswer | None = None, error=None):
        self.answer, self.error, self.calls = answer, error, []

    def invoke(self, role, messages, schema=None, tools=None):
        self.calls.append({"role": role, "messages": messages, "schema": schema})
        if self.error:
            raise self.error
        return LLMResult("", self.answer, [], "gemini", "m", 100, 20, 0.0, 5.0, False, 1, False)


GOOD = LLMAnswer(
    status="answered",
    answer="John Doman",
    claims=[
        Claim(text="John Doman starred in Emmett's Mark.", sources=["S1"]),
        Claim(text="John Doman played in The Wire.", sources=["S2"]),
    ],
)


def rag(retriever=None, gateway=None, min_relevance=0.05):
    return BaselineRAG(retriever or FakeRetriever(), gateway or FakeGateway(GOOD), min_relevance)


def test_answer_with_citations_mapped_to_chunks():
    gateway = FakeGateway(GOOD)
    a = rag(gateway=gateway).answer("Which Emmett's Mark actor was in The Wire?")
    assert (a.status, a.answer) == ("answered", "John Doman")
    assert [(c.label, c.chunk_id, c.title) for c in a.citations] == [
        ("S1", "c1", "Emmett's Mark"),
        ("S2", "c2", "John Doman"),
    ]
    assert a.usage["prompt_version"] == PROMPT_VERSION and a.usage["best_relevance"] == 0.9
    system = gateway.calls[0]["messages"][0]["content"]
    assert "[S1] Emmett's Mark" in system and "[S2] John Doman" in system
    assert gateway.calls[0]["schema"] is LLMAnswer and gateway.calls[0]["role"] == "answer"


def test_low_relevance_refuses_without_calling_the_llm():
    gateway = FakeGateway(GOOD)
    low = [chunk(1, "Seine", "A river.", ce=0.01)]
    a = rag(FakeRetriever(low), gateway).answer("Who won the 2030 World Cup?")
    assert a.status == "insufficient_evidence"
    assert gateway.calls == []
    assert [s.title for s in a.retrieved] == ["Seine"]  # still shown, for transparency


def test_model_insufficient_answer_keeps_its_explanation():
    reply = LLMAnswer(
        status="insufficient_evidence", answer="The sources do not name the director."
    )
    a = rag(gateway=FakeGateway(reply)).answer("Who directed it?")
    assert a.status == "insufficient_evidence"
    assert a.answer == "The sources do not name the director."


def test_answer_citing_nothing_valid_is_hidden():
    reply = LLMAnswer(status="answered", answer="Paris", claims=[Claim(text="x", sources=["S7"])])
    a = rag(gateway=FakeGateway(reply)).answer("q")
    assert a.status == "insufficient_evidence"
    assert a.answer == "I cannot answer this from the documents."
    assert a.citations == []


@pytest.mark.parametrize(
    "retriever, gateway, phrase",
    [
        (FakeRetriever(error=EmbeddingError("down")), FakeGateway(GOOD), "Search"),
        (FakeRetriever(), FakeGateway(error=LLMQuotaExceeded("daily")), "language model"),
    ],
)
def test_failures_return_unavailable_instead_of_raising(retriever, gateway, phrase):
    a = rag(retriever, gateway).answer("q")
    assert a.status == "unavailable" and phrase in a.answer
