"""LLM error types and the classification that drives retries (hand-written)."""

import re
from typing import Literal

from langchain_core.exceptions import ModelError


class LLMError(RuntimeError):
    """Base for every error the gateway raises."""


class LLMQuotaExceeded(LLMError):
    """A quota that will not recover soon: daily limit, or no billing/credit. Never retried."""


class LLMUnavailable(LLMError):
    """Still failing after all retries (rate limit, 5xx, timeout, connection)."""


class LLMBadOutput(LLMError):
    """The model answered, but not in the requested structured format."""


class LLMFatalError(LLMError):
    """Retrying cannot help: bad request, wrong key, unknown model."""


Action = Literal["retry", "quota", "fatal"]

# A 429 with these words is not "slow down", it is "you are out": retrying only wastes time.
_QUOTA_WORDS = ("insufficient_quota", "billing", "not active", "perday", "per day", "daily")
_RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


def _status(exc: BaseException) -> int | None:
    for attr in ("status_code", "code", "status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    match = re.search(r"\b(400|401|403|404|408|429|500|502|503|504)\b", str(exc))
    return int(match.group(1)) if match else None


def classify(exc: BaseException) -> Action:
    if isinstance(exc, LLMQuotaExceeded):
        return "quota"
    if isinstance(exc, LLMBadOutput):
        return "retry"  # a second sample often parses
    status = _status(exc)
    message = str(exc).lower()  # Gemini names the metric, e.g. "...RequestsPerDayPerProject..."
    if status == 429 and any(word in message for word in _QUOTA_WORDS):
        return "quota"
    if status in _RETRYABLE_STATUS:
        return "retry"
    if isinstance(exc, ModelError):  # LangChain's standard errors say whether to retry
        return "retry" if exc.is_retryable else "fatal"
    name = type(exc).__name__
    if "Timeout" in name or "Connection" in name:
        return "retry"
    return "fatal"


def retry_after_seconds(exc: BaseException) -> float | None:
    """Delay the provider asked for, if it said one (header or message text)."""
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None) or {}
    try:
        if "retry-after" in headers:
            return float(headers["retry-after"])
    except (TypeError, ValueError):
        pass
    # Gemini: "Please retry in 23.4s" or "retryDelay': '23s'"
    match = re.search(r"retry(?: in|Delay['\"]?:\s*['\"]?)\s*([\d.]+)s", str(exc))
    return float(match.group(1)) if match else None
