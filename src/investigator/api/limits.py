"""Request limits for the public demo (hand-written).

One limiter serves both the REST API and the Gradio UI, so neither can be used
to get around the other. Counts live in memory: a restart resets them, which
is acceptable for a demo, because the LLM gateway's own per-model daily budget
and the provider's quota still apply behind it.
"""

import time
from collections import deque
from collections.abc import Callable
from datetime import UTC, datetime


class LimitExceeded(Exception):
    """A client or the whole demo has used its allowance."""


class RequestLimiter:
    def __init__(
        self,
        per_minute: int,
        per_day_per_client: int,
        per_day_total: int | None = None,
        clock: Callable[[], float] = time.monotonic,
        today: Callable[[], str] = lambda: datetime.now(UTC).date().isoformat(),
    ):
        self.per_minute = per_minute
        self.per_day_per_client = per_day_per_client
        self.per_day_total = per_day_total
        self.clock = clock
        self.today = today
        self._recent: dict[str, deque[float]] = {}
        self._day = today()
        self._daily: dict[str, int] = {}
        self._total = 0

    def check(self, client: str) -> None:
        """Count one request for `client`, or raise LimitExceeded without counting it."""
        if self.today() != self._day:  # new day: reset the daily counts
            self._day, self._daily, self._total = self.today(), {}, 0

        if self.per_day_total is not None and self._total >= self.per_day_total:
            raise LimitExceeded(
                "The demo's daily question budget is used up (it protects the free LLM quota). "
                "Please try again tomorrow."
            )
        if self._daily.get(client, 0) >= self.per_day_per_client:
            raise LimitExceeded(f"Daily limit of {self.per_day_per_client} reached for you.")

        recent = self._recent.setdefault(client, deque())
        now = self.clock()
        while recent and now - recent[0] >= 60:
            recent.popleft()
        if len(recent) >= self.per_minute:
            wait = 60 - (now - recent[0])
            raise LimitExceeded(f"Too many requests; try again in {wait:.0f} s.")

        recent.append(now)
        self._daily[client] = self._daily.get(client, 0) + 1
        self._total += 1


def client_key(headers: dict, host: str | None) -> str:
    """Who is asking: the first X-Forwarded-For address (Render's proxy sets it), else the
    socket address. Clients can forge the header, which is acceptable for a demo limit."""
    forwarded = headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() or host or "unknown"
