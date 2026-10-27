"""Error classification, retries and rate limiting (no network, no real sleeping)."""

import pytest
from langchain_core.exceptions import ModelAuthenticationError, ModelRateLimitError

from investigator.llm.errors import (
    LLMBadOutput,
    LLMFatalError,
    LLMQuotaExceeded,
    LLMUnavailable,
    classify,
    retry_after_seconds,
)
from investigator.llm.ratelimit import RateLimiter
from investigator.llm.retry import RetryPolicy, backoff_delay, call_with_retries


class HTTPError(Exception):
    def __init__(self, status_code: int, message: str = ""):
        super().__init__(message or f"HTTP {status_code}")
        self.status_code = status_code


# ---- classification ------------------------------------------------------


@pytest.mark.parametrize(
    "exc, action",
    [
        (HTTPError(429, "Rate limit reached, slow down"), "retry"),
        (
            HTTPError(429, "You exceeded your quota: GenerateRequestsPerDayPerProjectPerModel"),
            "quota",
        ),
        (HTTPError(429, "insufficient_quota: check your plan and billing"), "quota"),
        (HTTPError(503, "overloaded"), "retry"),
        (HTTPError(400, "invalid argument"), "fatal"),
        (HTTPError(401, "bad key"), "fatal"),
        (TimeoutError(), "retry"),
        (ConnectionError(), "retry"),
        (LLMBadOutput("not json"), "retry"),
        (ValueError("a bug in our code"), "fatal"),
        (Exception("429 Too Many Requests"), "retry"),  # status only in the message
    ],
)
def test_classify(exc, action):
    assert classify(exc) == action


def test_classify_uses_langchain_standard_errors():
    assert classify(ModelRateLimitError("slow down")) == "retry"
    assert classify(ModelAuthenticationError("bad key")) == "fatal"


def test_retry_after_from_gemini_message():
    assert retry_after_seconds(Exception("Quota exceeded. Please retry in 23.4s.")) == 23.4
    assert retry_after_seconds(Exception("details: {'retryDelay': '7s'}")) == 7.0
    assert retry_after_seconds(Exception("no hint")) is None


# ---- retries -------------------------------------------------------------

POLICY = RetryPolicy(max_attempts=4, backoff_base_s=2.0, backoff_max_s=10.0)


def failing(errors: list[Exception], result="ok"):
    """A function that raises the given errors in turn, then returns result."""
    calls = []

    def fn():
        calls.append(1)
        if len(calls) <= len(errors):
            raise errors[len(calls) - 1]
        return result

    return fn, calls


def test_backoff_doubles_and_is_capped():
    no_jitter = [backoff_delay(a, POLICY, jitter=1.0) for a in range(1, 6)]
    assert no_jitter == [2.0, 4.0, 8.0, 10.0, 10.0]
    assert backoff_delay(1, POLICY, jitter=0.0) == 1.0  # jitter lowers it to 50% at most


def test_retries_then_succeeds_and_reports_attempts():
    fn, calls = failing([HTTPError(503), TimeoutError()])
    slept = []
    result, attempts = call_with_retries(fn, POLICY, sleep=slept.append, rng=lambda: 1.0)
    assert (result, attempts, len(calls)) == ("ok", 3, 3)
    assert slept == [2.0, 4.0]


def test_provider_retry_delay_is_used_but_capped():
    fn, _ = failing([Exception("429: retry in 3s"), Exception("429: retry in 99s")])
    slept = []
    call_with_retries(fn, POLICY, sleep=slept.append)
    assert slept == [3.0, 10.0]


def test_gives_up_after_max_attempts():
    fn, calls = failing([HTTPError(503)] * 10)
    with pytest.raises(LLMUnavailable, match="4 attempts"):
        call_with_retries(fn, POLICY, sleep=lambda s: None)
    assert len(calls) == 4


@pytest.mark.parametrize(
    "exc, expected",
    [(HTTPError(429, "insufficient_quota"), LLMQuotaExceeded), (HTTPError(401), LLMFatalError)],
)
def test_quota_and_fatal_errors_are_not_retried(exc, expected):
    fn, calls = failing([exc])
    with pytest.raises(expected):
        call_with_retries(fn, POLICY, sleep=lambda s: None)
    assert len(calls) == 1


# ---- rate limiter ----------------------------------------------------------


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def test_limiter_waits_when_minute_is_full():
    clock = FakeClock()
    limiter = RateLimiter({"m": (2, 100)}, clock=clock, sleep=clock.sleep, today=lambda: "d1")
    limiter.acquire("m")
    clock.now = 10.0
    limiter.acquire("m")
    clock.now = 20.0
    limiter.acquire("m")  # third call in the same minute: wait until the first is 60 s old
    assert clock.slept == [40.0]


def test_limiter_refuses_when_daily_budget_is_spent_and_resets_next_day():
    day = {"value": "d1"}
    clock = FakeClock()
    limiter = RateLimiter(
        {"m": (100, 2)}, clock=clock, sleep=clock.sleep, today=lambda: day["value"]
    )
    limiter.acquire("m")
    limiter.acquire("m")
    with pytest.raises(LLMQuotaExceeded, match="daily"):
        limiter.acquire("m")
    day["value"] = "d2"
    limiter.acquire("m")
    assert limiter.used_today("m") == 1


def test_limiter_ignores_models_without_limits():
    limiter = RateLimiter({})
    for _ in range(1000):
        limiter.acquire("paid-model")
