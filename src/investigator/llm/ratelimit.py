"""Client-side rate limiting per model (hand-written).

Free tiers allow N requests per minute and M per day. Waiting before a call is
cheaper than being refused and retrying, and refusing locally once the daily
budget is gone lets the gateway switch to the fallback model without a wasted
request. The day counter lives in memory, so it restarts with the process; the
provider still enforces the real limit, and its 429 is handled as quota.
"""

import time
from collections import deque
from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from investigator.llm.errors import LLMQuotaExceeded

PACIFIC = ZoneInfo("America/Los_Angeles")  # Gemini's daily quota resets at midnight Pacific


class RateLimiter:
    def __init__(
        self,
        limits: dict[str, tuple[int, int]],  # model -> (requests per minute, requests per day)
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        today: Callable[[], str] = lambda: datetime.now(PACIFIC).date().isoformat(),
    ):
        self.limits = limits
        self.clock = clock
        self.sleep = sleep
        self.today = today
        self._recent: dict[str, deque[float]] = {}  # call times within the last minute
        self._daily: dict[str, tuple[str, int]] = {}  # model -> (day, calls that day)

    def acquire(self, model: str) -> None:
        """Block until a call is allowed; raise LLMQuotaExceeded if today's budget is spent."""
        if model not in self.limits:
            return  # paid models: no local limit
        rpm, rpd = self.limits[model]

        day, used = self._daily.get(model, (self.today(), 0))
        if day != self.today():
            day, used = self.today(), 0
        if used >= rpd:
            raise LLMQuotaExceeded(f"Local daily budget of {rpd} requests for {model} is used up")

        recent = self._recent.setdefault(model, deque())
        now = self.clock()
        while recent and now - recent[0] >= 60:
            recent.popleft()
        if len(recent) >= rpm:
            self.sleep(60 - (now - recent[0]))  # wait until the oldest call leaves the window
            recent.popleft()

        recent.append(self.clock())
        self._daily[model] = (day, used + 1)

    def used_today(self, model: str) -> int:
        day, used = self._daily.get(model, ("", 0))
        return used if day == self.today() else 0
