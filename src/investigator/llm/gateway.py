"""LLMGateway: the one entry point for every LLM call (policy is hand-written).

    invoke(role, messages, schema=None, tools=None) -> LLMResult

For each model it tries (the role's model, then the fallback model):
  1. cache lookup        same request -> stored answer, no API call, no cost
  2. rate limiter        wait for a free slot; refuse if today's budget is spent
  3. call with retries   backoff on 429/5xx/timeouts; never retry quota or bad requests
  4. log                 one JSONL line: role, model, tokens, cost, latency, cache hit
If the role's model fails for good, the fallback model is tried. The judge role
never falls back, because grading with a different model would change the grades.
"""

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import BaseModel

from investigator.config import PROJECT_ROOT, LLMConfig, ModelSpec
from investigator.llm.backends import ChatBackend, RawResponse
from investigator.llm.cache import ResponseCache, cache_key
from investigator.llm.errors import LLMError
from investigator.llm.pricing import Pricing
from investigator.llm.ratelimit import RateLimiter
from investigator.llm.retry import RetryPolicy, call_with_retries

Role = Literal["planner", "answer", "grader", "fallback", "judge"]
NO_FALLBACK: set[str] = {"judge", "fallback"}


@dataclass
class LLMResult:
    text: str
    parsed: BaseModel | None
    tool_calls: list[dict]
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float | None  # 0 when served from cache: nothing was spent
    latency_ms: float
    cached: bool
    attempts: int
    fell_back: bool


@dataclass
class UsageTotals:
    calls: int = 0
    cached_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    by_model: dict[str, dict] = field(default_factory=dict)


class LLMGateway:
    def __init__(
        self,
        cfg: LLMConfig,
        backend_factory: Callable[[ModelSpec], ChatBackend],
        pricing: Pricing,
        cache: ResponseCache | None = None,
        limiter: RateLimiter | None = None,
        sleep: Callable[[float], None] = time.sleep,
        log_path: Path | None = None,
    ):
        self.cfg = cfg
        self.backend_factory = backend_factory
        self.pricing = pricing
        self.cache = cache
        self.limiter = limiter or RateLimiter({}, sleep=sleep)
        self.sleep = sleep
        self.policy = RetryPolicy(**cfg.retry.model_dump())
        self.log_path = log_path
        self.usage = UsageTotals()
        self._backends: dict[str, ChatBackend] = {}

    def invoke(
        self,
        role: Role,
        messages: list[dict],
        schema: type[BaseModel] | None = None,
        tools: list | None = None,
    ) -> LLMResult:
        specs = [getattr(self.cfg, role)]
        if role not in NO_FALLBACK and self.cfg.fallback != specs[0]:
            specs.append(self.cfg.fallback)

        last_error: LLMError | None = None
        for i, spec in enumerate(specs):
            try:
                return self._invoke_model(role, spec, messages, schema, tools, fell_back=i > 0)
            except LLMError as err:
                last_error = err
                self._log({"role": role, "model": spec.name, "error": type(err).__name__,
                           "detail": str(err)[:300]})  # fmt: skip
        raise last_error

    def _invoke_model(self, role, spec, messages, schema, tools, fell_back) -> LLMResult:
        request = {
            "provider": spec.provider,
            "model": spec.name,
            "temperature": spec.temperature,
            "reasoning_effort": spec.reasoning_effort,
            "messages": messages,
            "schema": schema.model_json_schema() if schema else None,
            "tools": [convert_to_openai_tool(t) for t in tools] if tools else None,
        }
        key = cache_key(request)
        start = time.perf_counter()

        stored = self.cache.get(key) if self.cache else None
        if stored is not None:
            raw, attempts, cached = RawResponse(**stored), 0, True
        else:
            backend = self._backend(spec)

            def call() -> RawResponse:
                self.limiter.acquire(spec.name)  # every attempt counts against the limits
                return backend.invoke(messages, schema, tools)

            raw, attempts = call_with_retries(call, self.policy, sleep=self.sleep)
            cached = False
            if self.cache:
                self.cache.put(key, raw.__dict__)

        cost = 0.0 if cached else self.pricing.cost(spec.name, raw.input_tokens, raw.output_tokens)
        result = LLMResult(
            text=raw.text,
            parsed=schema.model_validate(raw.parsed) if schema else None,
            tool_calls=raw.tool_calls,
            provider=spec.provider,
            model=spec.name,
            input_tokens=raw.input_tokens,
            output_tokens=raw.output_tokens,
            cost_usd=cost,
            latency_ms=round((time.perf_counter() - start) * 1000, 1),
            cached=cached,
            attempts=attempts,
            fell_back=fell_back,
        )
        self._record(role, result)
        return result

    def _backend(self, spec: ModelSpec) -> ChatBackend:
        # Keyed by the whole spec, not the name: the judge and the fallback can be the
        # same model with different settings (reasoning effort) and need separate clients.
        key = spec.model_dump_json()
        if key not in self._backends:
            self._backends[key] = self.backend_factory(spec)
        return self._backends[key]

    def _record(self, role: str, r: LLMResult) -> None:
        u = self.usage
        u.calls += 1
        u.cached_calls += r.cached
        if not r.cached:
            u.input_tokens += r.input_tokens
            u.output_tokens += r.output_tokens
            u.cost_usd += r.cost_usd or 0.0
        m = u.by_model.setdefault(r.model, {"calls": 0, "input_tokens": 0, "output_tokens": 0,
                                            "cost_usd": 0.0})  # fmt: skip
        m["calls"] += 1
        if not r.cached:
            m["input_tokens"] += r.input_tokens
            m["output_tokens"] += r.output_tokens
            m["cost_usd"] += r.cost_usd or 0.0
        self._log({"role": role, "provider": r.provider, "model": r.model,
                   "input_tokens": r.input_tokens, "output_tokens": r.output_tokens,
                   "cost_usd": r.cost_usd, "latency_ms": r.latency_ms, "cached": r.cached,
                   "attempts": r.attempts, "fell_back": r.fell_back})  # fmt: skip

    def _log(self, entry: dict) -> None:
        if self.log_path is None:
            return
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {"time": datetime.now(UTC).isoformat(timespec="seconds"), **entry}
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")


def make_gateway(cfg: LLMConfig, secrets) -> LLMGateway:
    """Production wiring: real backends, on-disk cache, free-tier limits, JSONL log."""
    from investigator.llm.backends import make_backend

    return LLMGateway(
        cfg,
        backend_factory=lambda spec: make_backend(spec, secrets, cfg.timeout_s),
        pricing=Pricing.load(),
        cache=ResponseCache(PROJECT_ROOT / cfg.cache_path),
        limiter=RateLimiter(dict(cfg.rate_limits)),
        log_path=PROJECT_ROOT / cfg.log_path,
    )
