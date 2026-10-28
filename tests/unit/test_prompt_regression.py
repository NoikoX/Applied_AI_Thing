"""Prompt regression tests (offline, run in CI).

1. Fingerprints: every prompt version is pinned to a hash of its text and its
   output schema. Editing a prompt without bumping its version fails here, so
   prompt changes are always deliberate and visible in review.
2. Replay: real LLM responses and searches recorded for one golden question per
   category (tests/replay/cassette.json) are replayed through the baseline and
   the agent. Any change in a rendered prompt (no matching recording) or in the
   pipeline's outcome (status, answer, citations) fails the test.
"""

import hashlib
import json

import pytest

from investigator.agent import prompts as agent_prompts
from investigator.agent import schemas as agent_schemas
from investigator.config import PROJECT_ROOT
from investigator.evaluation import judge
from investigator.evaluation.replay import ReplayGateway, ReplayRetriever, outcome
from investigator.evaluation.systems import make_system
from investigator.rag import prompts as rag_prompts
from investigator.rag.schemas import LLMAnswer

# version -> fingerprint. When you change a prompt: bump its version, run the test,
# paste the new fingerprint here, and re-record the cassette (scripts/record_replay.py).
PINNED = {
    "answer-v1": "904d2a45e0d1631b",
    "agent-v1": "c6ae20795a801b3f",
    "judge-v1": "f49aad641f4c61ff",
}
CASSETTE = PROJECT_ROOT / "tests" / "replay" / "cassette.json"


def fingerprint(*parts) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()[:16]


def current_fingerprints() -> dict[str, str]:
    a, s = agent_prompts, agent_schemas
    return {
        rag_prompts.PROMPT_VERSION: fingerprint(
            rag_prompts.ANSWER_SYSTEM, LLMAnswer.model_json_schema()
        ),
        a.AGENT_PROMPT_VERSION: fingerprint(
            a.PLAN_SYSTEM,
            a.RETRIEVE_SYSTEM,
            a.GRADE_SYSTEM,
            a.EXTRACT_SYSTEM,
            a.CONFLICT_NOTE,
            s.Plan.model_json_schema(),
            s.Grade.model_json_schema(),
            s.ClaimList.model_json_schema(),
            s.search_documents.model_json_schema(),
        ),  # fmt: skip
        judge.JUDGE_PROMPT_VERSION: fingerprint(
            judge.JUDGE_SYSTEM, judge.Verdict.model_json_schema()
        ),
    }


@pytest.mark.parametrize("version", list(current_fingerprints()))
def test_prompt_text_matches_its_pinned_version(version):
    assert version in PINNED, f"New prompt version {version}: add its fingerprint to PINNED."
    assert current_fingerprints()[version] == PINNED[version], (
        f"Prompt {version} changed without a version bump. Bump the version, update PINNED, "
        "and re-record tests/replay/cassette.json."
    )


def _cases():
    if not CASSETTE.exists():
        return []
    expected = json.loads(CASSETTE.read_text(encoding="utf-8"))["expected"]
    return [(system, item_id) for system, items in expected.items() for item_id in items]


@pytest.mark.parametrize("system, item_id", _cases())
def test_replay_reproduces_recorded_outcome(system, item_id):
    cassette = json.loads(CASSETTE.read_text(encoding="utf-8"))
    qa = make_system(system, ReplayGateway(cassette["llm"]), ReplayRetriever(cassette["searches"]))
    recorded = cassette["expected"][system][item_id]
    assert outcome(qa.answer(recorded["question"])) == {
        k: v for k, v in recorded.items() if k != "question"
    }
