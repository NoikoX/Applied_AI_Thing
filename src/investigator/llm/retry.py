"""Retry with exponential backoff and jitter (hand-written).

The provider SDKs' own retries are switched off (max_retries=0), so this is
the single place that decides when to try again and how long to wait.
"""

import random
import time
from collections.abc import Callable
from dataclasses import dataclass

from investigator.llm.errors import (
    LLMError,
    LLMFatalError,
    LLMQuotaExceeded,
    LLMUnavailable,
    classify,
    retry_after_seconds,
)


@dataclass
class RetryPolicy:
    max_attempts: int
    backoff_base_s: float
    backoff_max_s: float


def backoff_delay(attempt: int, policy: RetryPolicy, jitter: float) -> float:
    """attempt 1 -> base, 2 -> 2*base, 3 -> 4*base ... capped; jitter in [0, 1) scales
    it to 50-100%, so many clients hitting the same limit do not retry in lockstep."""
    delay = min(policy.backoff_max_s, policy.backoff_base_s * 2 ** (attempt - 1))
    return delay * (0.5 + jitter / 2)


def call_with_retries[T](
    fn: Callable[[], T],
    policy: RetryPolicy,
    sleep: Callable[[float], None] = time.sleep,
    rng: Callable[[], float] = random.random,
) -> tuple[T, int]:
    """Run fn until it succeeds; return (result, attempts used).

    quota -> raise LLMQuotaExceeded at once; fatal -> raise LLMFatalError at once;
    retry -> wait (the provider's Retry-After if given, else backoff) and try again,
    raising LLMUnavailable after the last attempt.
    """
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return fn(), attempt
        except Exception as exc:
            action = classify(exc)
            if action == "quota":
                raise (
                    exc if isinstance(exc, LLMQuotaExceeded) else LLMQuotaExceeded(str(exc))
                ) from exc
            if action == "fatal":
                raise exc if isinstance(exc, LLMError) else LLMFatalError(str(exc)) from exc
            if attempt == policy.max_attempts:
                raise LLMUnavailable(f"Failed after {attempt} attempts: {exc}") from exc
            asked = retry_after_seconds(exc)
            delay = (
                min(asked, policy.backoff_max_s) if asked else backoff_delay(attempt, policy, rng())
            )
            sleep(delay)
    raise AssertionError("unreachable")
