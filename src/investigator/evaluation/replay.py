"""Record real LLM calls and searches once; replay them offline in CI.

The replay is keyed by the exact request (role, full prompt text, output schema,
tool names; or query + sub-queries for search). So the CI test fails when
  - a prompt's wording changes (no recording for the new prompt), or
  - pipeline logic changes the outcome (status, answer, citations differ),
which is what a prompt regression test should catch. Re-record deliberately with
scripts/record_replay.py and review the diff of tests/replay/cassette.json.
"""

import hashlib
import json
from dataclasses import asdict

from pydantic import BaseModel

from investigator.llm.gateway import LLMResult
from investigator.retrieval.candidate import Candidate
from investigator.retrieval.search import RetrievalResult


class ReplayMiss(AssertionError):
    """No recording matches this request: a prompt or the pipeline changed."""


def _hash(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def llm_key(role, messages, schema, tools) -> str:
    tool_names = [getattr(t, "__name__", str(t)) for t in tools or []]
    return _hash([role, messages, schema.__name__ if schema else None, tool_names])


def search_key(question, subqueries) -> str:
    return _hash([question, list(subqueries or [])])


class RecordingGateway:
    def __init__(self, inner):
        self.inner = inner
        self.llm: dict[str, dict] = {}

    def invoke(self, role, messages, schema=None, tools=None) -> LLMResult:
        r = self.inner.invoke(role, messages, schema=schema, tools=tools)
        self.llm[llm_key(role, messages, schema, tools)] = {
            "role": role,
            "text": r.text,
            "parsed": r.parsed.model_dump() if isinstance(r.parsed, BaseModel) else None,
            "tool_calls": r.tool_calls,
            "model": r.model,
        }
        return r


class ReplayGateway:
    def __init__(self, llm: dict[str, dict]):
        self.llm = llm

    def invoke(self, role, messages, schema=None, tools=None) -> LLMResult:
        rec = self.llm.get(llm_key(role, messages, schema, tools))
        if rec is None:
            raise ReplayMiss(
                f"No recorded '{role}' call for this prompt. If a prompt or the pipeline changed "
                "on purpose, re-record with scripts/record_replay.py and review the diff."
            )
        parsed = schema.model_validate(rec["parsed"]) if schema else None
        return LLMResult(rec["text"], parsed, rec["tool_calls"], "replay", rec["model"],
                         0, 0, 0.0, 0.0, True, 0, False)  # fmt: skip


def _dump(result: RetrievalResult) -> dict:
    chunks = []
    for c in result.chunks:
        d = asdict(c)
        d["covers"] = sorted(d["covers"])
        d["vector"] = None  # not needed downstream, and large
        chunks.append(d)
    return {"chunks": chunks, "stopped_early": result.stopped_early,
            "n_candidates": result.n_candidates}  # fmt: skip


def _load(data: dict) -> RetrievalResult:
    chunks = [Candidate(**{**c, "covers": set(c["covers"])}) for c in data["chunks"]]
    return RetrievalResult(chunks, data["stopped_early"], data["n_candidates"], {})


class RecordingRetriever:
    def __init__(self, inner):
        self.inner = inner
        self.searches: dict[str, dict] = {}

    def search(self, question, subqueries=None) -> RetrievalResult:
        result = self.inner.search(question, subqueries=subqueries)
        self.searches[search_key(question, subqueries)] = _dump(result)
        return result


class ReplayRetriever:
    def __init__(self, searches: dict[str, dict]):
        self.searches = searches

    def search(self, question, subqueries=None) -> RetrievalResult:
        data = self.searches.get(search_key(question, subqueries))
        if data is None:
            raise ReplayMiss(f"No recorded search for {question!r} with {subqueries!r}.")
        return _load(data)


def outcome(answer) -> dict:
    """The parts of an answer the regression test compares."""
    return {"status": answer.status, "answer": answer.answer,
            "cited_doc_ids": [c.doc_id for c in answer.citations]}  # fmt: skip
