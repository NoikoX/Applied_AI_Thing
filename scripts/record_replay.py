"""Record the CI replay cassette: real LLM calls and searches for a few golden questions.

    uv run python scripts/record_replay.py

Writes tests/replay/cassette.json. Review its diff before committing: it is the
behaviour the prompt regression test will hold the code to.
"""

import json

from investigator.config import PROJECT_ROOT
from investigator.evaluation.replay import RecordingGateway, RecordingRetriever, outcome
from investigator.evaluation.systems import make_parts, make_system

IDS = ["G01", "G11", "G19", "G26", "G32", "G36"]  # bridge, comparison, unanswerable,
# contradictory, injection, simple: one per category
OUT = PROJECT_ROOT / "tests" / "replay" / "cassette.json"


def main() -> None:
    golden = (PROJECT_ROOT / "eval/golden/golden.jsonl").read_text(encoding="utf-8")
    items = {i["id"]: i for i in map(json.loads, golden.splitlines())}
    # A fast model is fine: replay checks that prompts and outcomes do not change,
    # not which model produced them.
    gateway, retriever, _, _ = make_parts("mini", "golden__large")
    rec_gateway, rec_retriever = RecordingGateway(gateway), RecordingRetriever(retriever)

    expected: dict[str, dict] = {}
    for name in ("baseline", "agent"):
        system = make_system(name, rec_gateway, rec_retriever)
        expected[name] = {}
        for item_id in IDS:
            question = items[item_id]["question"]
            expected[name][item_id] = {"question": question, **outcome(system.answer(question))}
            print(name, item_id, expected[name][item_id]["status"], flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    cassette = {"llm": rec_gateway.llm, "searches": rec_retriever.searches, "expected": expected}
    OUT.write_text(json.dumps(cassette, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(rec_gateway.llm)} LLM calls, {len(rec_retriever.searches)} searches)")


if __name__ == "__main__":
    main()
