"""The LangGraph agent end to end, with scripted LLM steps and a keyword retriever."""

from investigator.agent.graph import InvestigationAgent
from investigator.agent.nodes import Deps
from investigator.agent.schemas import ClaimList, ExtractedClaim, Grade, Plan
from investigator.config import load_config
from investigator.index.embeddings import EmbeddingError
from investigator.llm.errors import LLMUnavailable
from investigator.llm.gateway import LLMResult
from investigator.rag.schemas import Claim, LLMAnswer
from investigator.retrieval.candidate import Candidate
from investigator.retrieval.search import RetrievalResult

CFG = load_config()
QUESTION = "What was the nationality of the philosopher whose philosophy Harry Jaffa developed?"

PASSAGES = {
    "jaffa": Candidate("c1", "hp_jaffa", "Harry V. Jaffa",
                       "Jaffa applied the philosophy of Leo Strauss to American politics.", {},
                       ce=0.9),
    "strauss": Candidate("c2", "hp_strauss", "Leo Strauss",
                         "Leo Strauss was a German-American political philosopher.", {}, ce=0.8),
}  # fmt: skip


class KeywordRetriever:
    """Returns the passages whose key appears in any sub-query."""

    def __init__(self, error=None):
        self.calls, self.error = [], error

    def search(self, question, subqueries=None):
        self.calls.append(subqueries)
        if self.error:
            raise self.error
        text = " ".join(subqueries or [question]).lower()
        chunks = [c for key, c in PASSAGES.items() if key in text]
        return RetrievalResult(chunks, False, len(chunks), {"search": 1.0})


def result(parsed=None, tool_calls=None) -> LLMResult:
    return LLMResult(
        "", parsed, tool_calls or [], "gemini", "m", 100, 10, 0.0, 3.0, False, 1, False
    )


def search_call(query: str) -> dict:
    return {"name": "search_documents", "args": {"query": query}, "id": query}


class ScriptedGateway:
    """Replies by step: (role, output schema name or 'tools') -> list of replies used in order."""

    def __init__(self, script: dict):
        self.script = {k: list(v) for k, v in script.items()}
        self.calls = []

    def invoke(self, role, messages, schema=None, tools=None):
        key = (role, "tools" if tools else schema.__name__)
        self.calls.append({"key": key, "messages": messages})
        replies = self.script[key]
        reply = replies.pop(0) if len(replies) > 1 else replies[0]
        if isinstance(reply, Exception):
            raise reply
        return reply


PLAN = result(
    Plan(
        question_type="bridge",
        sub_questions=[
            "Whose philosophy did Harry Jaffa develop?",
            "What was that philosopher's nationality?",
        ],
    )
)
INSUFFICIENT = result(
    Grade(
        sufficient=False,
        missing="the philosopher's nationality",
        follow_up_queries=["Leo Strauss nationality"],
    )
)
SUFFICIENT = result(Grade(sufficient=True))


def fact(subject, attribute, value, source) -> ExtractedClaim:
    return ExtractedClaim(
        subject=subject, attribute=attribute, value=value, source=source, single_valued=True
    )


CLAIMS = result(ClaimList(claims=[fact("Leo Strauss", "nationality", "German-American", "S2")]))
ANSWER = result(LLMAnswer(status="answered", answer="German-American", claims=[
    Claim(text="Jaffa developed Leo Strauss's philosophy.", sources=["S1"]),
    Claim(text="Strauss was German-American.", sources=["S2"])]))  # fmt: skip


def script(overrides: dict | None = None):
    base = {
        ("planner", "Plan"): [PLAN],
        ("planner", "tools"): [result(tool_calls=[search_call("Harry Jaffa philosophy")]),
                               result(tool_calls=[search_call("Leo Strauss nationality")])],
        ("grader", "Grade"): [INSUFFICIENT, SUFFICIENT],
        ("grader", "ClaimList"): [CLAIMS],
        ("answer", "LLMAnswer"): [ANSWER],
    }  # fmt: skip
    return {**base, **(overrides or {})}


def agent(gateway, retriever=None, **cfg_overrides):
    retriever = retriever or KeywordRetriever()
    cfg = CFG.agent.model_copy(update=cfg_overrides)
    return InvestigationAgent(Deps(gateway, retriever, cfg, CFG.rag.min_relevance)), retriever


def steps(answer) -> list[str]:
    return [s["step"] for s in answer.usage["trace"]]


def test_bridge_question_takes_a_second_hop_and_answers():
    gateway = ScriptedGateway(script())
    a, retriever = agent(gateway)
    answer = a.answer(QUESTION)
    assert answer.status == "answered" and answer.answer == "German-American"
    assert steps(answer) == ["plan", "retrieve-1", "grade-1", "retrieve-2", "grade-2",
                             "extract", "answer"]  # fmt: skip
    # The second hop searched for the entity found in the first hop.
    assert retriever.calls == [["Harry Jaffa philosophy"], ["Leo Strauss nationality"]]
    assert [c.title for c in answer.citations] == ["Harry V. Jaffa", "Leo Strauss"]
    assert answer.usage["hops"] == 2 and answer.usage["llm_calls"] == 7
    # What hop 1 found is shown to the model choosing hop 2's searches.
    hop2_prompt = [c for c in gateway.calls if c["key"] == ("planner", "tools")][1]
    assert "Leo Strauss" in hop2_prompt["messages"][1]["content"]


def test_stops_after_max_hops_even_if_still_insufficient():
    gateway = ScriptedGateway(script({("grader", "Grade"): [INSUFFICIENT]}))
    answer = agent(gateway, max_hops=1)[0].answer(QUESTION)
    assert steps(answer).count("grade-1") == 1 and "retrieve-2" not in steps(answer)


def test_no_tool_call_falls_back_to_the_plan_sub_questions():
    gateway = ScriptedGateway(script({("planner", "tools"): [result(tool_calls=[])],
                                        ("grader", "Grade"): [SUFFICIENT]}))  # fmt: skip
    answer, retriever = None, KeywordRetriever()
    answer = agent(gateway, retriever)[0].answer(QUESTION)
    assert retriever.calls[0] == PLAN.parsed.sub_questions
    assert "no tool call" in answer.usage["trace"][1]["note"]


def test_planner_failure_uses_the_question_itself():
    gateway = ScriptedGateway(script({("planner", "Plan"): [LLMUnavailable("down")]}))
    answer = agent(gateway)[0].answer(QUESTION)
    assert answer.usage["trace"][0]["sub_questions"] == [QUESTION]
    assert answer.status == "answered"


def test_grader_failure_stops_searching():
    gateway = ScriptedGateway(script({("grader", "Grade"): [LLMUnavailable("down")]}))
    answer = agent(gateway)[0].answer(QUESTION)
    assert "retrieve-2" not in steps(answer)


def test_conflicting_claims_turn_an_answer_into_contradictory():
    conflicting = result(
        ClaimList(
            claims=[
                fact("Leo Strauss", "nationality", "German-American", "S2"),
                fact("Leo Strauss", "nationality", "French", "S1"),
            ]
        )
    )
    gateway = ScriptedGateway(script({("grader", "ClaimList"): [conflicting]}))
    answer = agent(gateway)[0].answer(QUESTION)
    assert answer.status == "contradictory"
    assert answer.usage["contradiction_source"] == "claims"
    answer_prompt = [c for c in gateway.calls if c["key"] == ("answer", "LLMAnswer")][0]
    assert "disagreements" in answer_prompt["messages"][0]["content"]


def test_unconfirmed_model_contradiction_is_kept_with_a_warning():
    reply = result(LLMAnswer(status="contradictory", answer="Sources disagree.",
                             claims=[Claim(text="x", sources=["S1"])]))  # fmt: skip
    gateway = ScriptedGateway(script({("answer", "LLMAnswer"): [reply]}))
    answer = agent(gateway)[0].answer(QUESTION)
    assert answer.status == "contradictory"
    assert answer.usage["contradiction_source"] == "model"
    assert any("did not find" in w for w in answer.warnings)


def test_extraction_drops_claims_citing_unknown_sources():
    bogus = result(ClaimList(claims=[fact("a", "b", "c", "S99")]))
    gateway = ScriptedGateway(script({("grader", "ClaimList"): [bogus]}))
    answer = agent(gateway)[0].answer(QUESTION)
    assert [s for s in answer.usage["trace"] if s["step"] == "extract"][0]["n_claims"] == 0


def test_answer_failure_is_unavailable():
    gateway = ScriptedGateway(script({("answer", "LLMAnswer"): [LLMUnavailable("down")]}))
    answer = agent(gateway)[0].answer(QUESTION)
    assert answer.status == "unavailable"


def test_search_failure_leads_to_refusal_not_a_crash():
    gateway = ScriptedGateway(script({("grader", "Grade"): [SUFFICIENT]}))
    answer = agent(gateway, KeywordRetriever(error=EmbeddingError("down")))[0].answer(QUESTION)
    assert answer.status == "insufficient_evidence"
    assert not any(c["key"] == ("answer", "LLMAnswer") for c in gateway.calls)
