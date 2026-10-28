import json

import pytest
from pydantic import BaseModel

from investigator.config import ModelSpec, load_config
from investigator.llm.backends import RawResponse, to_langchain
from investigator.llm.cache import ResponseCache, cache_key
from investigator.llm.errors import LLMQuotaExceeded, LLMUnavailable
from investigator.llm.gateway import LLMGateway
from investigator.llm.pricing import Pricing

# Distinct model names per role, so a scripted backend can be picked by name.
CFG = load_config().llm.model_copy(
    update={
        "planner": ModelSpec(provider="gemini", name="planner-model"),
        "answer": ModelSpec(provider="gemini", name="answer-model"),
        "fallback": ModelSpec(provider="openai", name="fallback-model", temperature=None),
        "judge": ModelSpec(provider="openai", name="judge-model", temperature=None),
    }
)
PRICING = Pricing.load()
MESSAGES = [{"role": "user", "content": "Who directed Emmett's Mark?"}]


class Plan(BaseModel):
    sub_questions: list[str]


class ScriptedBackend:
    """Returns (or raises) the scripted items in order; records every call."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def invoke(self, messages, schema, tools):
        self.calls.append({"messages": messages, "schema": schema, "tools": tools})
        item = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        if isinstance(item, Exception):
            raise item
        return item


def ok(text="answer", **kw) -> RawResponse:
    return RawResponse(text=text, input_tokens=1000, output_tokens=100, **kw)


def make_gateway(scripts: dict, tmp_path=None):
    backends = {name: ScriptedBackend(script) for name, script in scripts.items()}
    gateway = LLMGateway(
        CFG,
        backend_factory=lambda spec: backends[spec.name],
        pricing=PRICING,
        cache=ResponseCache(tmp_path / "cache.sqlite") if tmp_path else None,
        sleep=lambda s: None,
        log_path=tmp_path / "calls.jsonl" if tmp_path else None,
    )
    return gateway, backends


PRIMARY, FALLBACK = CFG.answer.name, CFG.fallback.name


def test_same_model_with_different_settings_gets_its_own_client():
    # Regression: judge and fallback were both gpt-5-mini with different reasoning effort,
    # and a client cache keyed by model name would have shared one client between them.
    def mini(effort):
        return ModelSpec(provider="openai", name="gpt-5-mini", temperature=None,
                         reasoning_effort=effort)  # fmt: skip

    cfg = CFG.model_copy(update={"fallback": mini("minimal"), "judge": mini("low")})
    created = []

    def factory(spec):
        created.append(spec.reasoning_effort)
        return ScriptedBackend([ok()])

    gateway = LLMGateway(cfg, backend_factory=factory, pricing=PRICING, sleep=lambda s: None)
    gateway.invoke("fallback", MESSAGES)
    gateway.invoke("judge", MESSAGES)
    assert created == ["minimal", "low"]


def test_successful_call_reports_tokens_and_cost():
    gateway, _ = make_gateway({PRIMARY: [ok()]})
    r = gateway.invoke("answer", MESSAGES)
    assert (r.text, r.model, r.cached, r.fell_back, r.attempts) == (
        "answer",
        PRIMARY,
        False,
        False,
        1,
    )
    assert r.cost_usd == PRICING.cost(PRIMARY, 1000, 100)


def test_second_identical_call_is_served_from_cache(tmp_path):
    gateway, backends = make_gateway({PRIMARY: [ok()]}, tmp_path)
    gateway.invoke("answer", MESSAGES)
    again = gateway.invoke("answer", MESSAGES)
    assert again.cached is True and again.cost_usd == 0.0
    assert len(backends[PRIMARY].calls) == 1
    assert gateway.usage.calls == 2 and gateway.usage.cached_calls == 1


def test_cache_survives_a_new_gateway(tmp_path):
    first, _ = make_gateway({PRIMARY: [ok("stored")]}, tmp_path)
    first.invoke("answer", MESSAGES)
    second, backends = make_gateway({PRIMARY: [ok("fresh")]}, tmp_path)
    assert second.invoke("answer", MESSAGES).text == "stored"
    assert backends[PRIMARY].calls == []


def test_retryable_error_is_retried_on_the_same_model():
    gateway, backends = make_gateway({PRIMARY: [TimeoutError(), ok()]})
    r = gateway.invoke("answer", MESSAGES)
    assert (r.model, r.attempts, r.fell_back) == (PRIMARY, 2, False)


def test_quota_error_switches_to_fallback_without_retrying(tmp_path):
    quota = Exception("429 RESOURCE_EXHAUSTED: GenerateRequestsPerDayPerProjectPerModel")
    gateway, backends = make_gateway({PRIMARY: [quota], FALLBACK: [ok("from fallback")]}, tmp_path)
    r = gateway.invoke("answer", MESSAGES)
    assert (r.text, r.model, r.fell_back) == ("from fallback", FALLBACK, True)
    assert len(backends[PRIMARY].calls) == 1
    log = [json.loads(line) for line in (tmp_path / "calls.jsonl").read_text().splitlines()]
    assert log[0]["error"] == "LLMQuotaExceeded" and log[1]["model"] == FALLBACK


def test_judge_never_falls_back():
    gateway, backends = make_gateway({CFG.judge.name: [TimeoutError()], FALLBACK: [ok()]})
    with pytest.raises(LLMUnavailable):
        gateway.invoke("judge", MESSAGES)
    assert FALLBACK not in backends or backends[FALLBACK].calls == []


def test_last_error_raised_when_every_model_fails():
    quota = Exception("429 insufficient_quota")
    gateway, _ = make_gateway({PRIMARY: [quota], FALLBACK: [quota]})
    with pytest.raises(LLMQuotaExceeded):
        gateway.invoke("answer", MESSAGES)


def test_structured_output_is_parsed_into_the_schema():
    reply = ok(parsed={"sub_questions": ["Who starred?", "Which series?"]})
    gateway, backends = make_gateway({CFG.planner.name: [reply]})
    r = gateway.invoke("planner", MESSAGES, schema=Plan)
    assert isinstance(r.parsed, Plan) and r.parsed.sub_questions[1] == "Which series?"
    assert backends[CFG.planner.name].calls[0]["schema"] is Plan


def test_tool_calls_pass_through():
    call = {"name": "search_documents", "args": {"query": "John Doman"}, "id": "c1"}
    gateway, _ = make_gateway({PRIMARY: [ok(text="", tool_calls=[call])]})
    assert gateway.invoke("answer", MESSAGES, tools=[Plan]).tool_calls == [call]


def test_cache_key_depends_on_everything_that_changes_the_answer():
    base = {"model": "m", "messages": MESSAGES, "temperature": 0.0}
    assert cache_key(base) == cache_key(dict(reversed(list(base.items()))))  # order-independent
    assert cache_key(base) != cache_key({**base, "model": "other"})
    assert cache_key(base) != cache_key({**base, "temperature": 0.5})


def test_pricing():
    assert PRICING.cost("gpt-5-nano", 1_000_000, 1_000_000) == pytest.approx(0.45)
    assert PRICING.cost("unknown-model", 10, 10) is None


def test_messages_convert_to_langchain_types():
    msgs = to_langchain(
        [
            {"role": "system", "content": "be brief"},
            {"role": "user", "content": "q"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"name": "t", "args": {}, "id": "1"}],
            },
            {"role": "tool", "content": "result", "tool_call_id": "1"},
        ]
    )
    assert [m.type for m in msgs] == ["system", "human", "ai", "tool"]
    with pytest.raises(ValueError):
        to_langchain([{"role": "robot", "content": "x"}])
