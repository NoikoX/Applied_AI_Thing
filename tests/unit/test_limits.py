import pytest

from investigator.api.limits import LimitExceeded, RequestLimiter, client_key


class Clock:
    def __init__(self):
        self.now = 0.0
        self.day = "d1"

    def __call__(self):
        return self.now


def limiter(per_minute=2, per_day=5, total=None):
    clock = Clock()
    return RequestLimiter(per_minute, per_day, total, clock=clock, today=lambda: clock.day), clock


def test_per_minute_window_slides():
    lim, clock = limiter(per_minute=2)
    lim.check("a")
    lim.check("a")
    with pytest.raises(LimitExceeded, match="try again in 60"):
        lim.check("a")
    clock.now = 60.0
    lim.check("a")  # the first request left the window


def test_refused_requests_do_not_count():
    lim, clock = limiter(per_minute=1, per_day=2)
    lim.check("a")
    for _ in range(5):
        with pytest.raises(LimitExceeded):
            lim.check("a")
    clock.now = 61.0
    lim.check("a")  # still allowed: only 2 counted today


def test_daily_limit_per_client_and_reset_next_day():
    lim, clock = limiter(per_minute=100, per_day=2)
    lim.check("a")
    lim.check("a")
    with pytest.raises(LimitExceeded, match="Daily limit"):
        lim.check("a")
    lim.check("b")  # another client is unaffected
    clock.day = "d2"
    lim.check("a")


def test_total_daily_budget_across_clients():
    lim, _ = limiter(per_minute=100, per_day=100, total=2)
    lim.check("a")
    lim.check("b")
    with pytest.raises(LimitExceeded, match="budget"):
        lim.check("c")


def test_client_key_prefers_forwarded_address():
    assert client_key({"x-forwarded-for": "9.9.9.9, 10.0.0.1"}, "10.0.0.1") == "9.9.9.9"
    assert client_key({}, "127.0.0.1") == "127.0.0.1"
    assert client_key({}, None) == "unknown"
