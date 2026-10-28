"""Apply the hand review in eval/golden/review_decisions.json to eval/golden/golden.jsonl.

    uv run python scripts/build_golden.py          # draft (verified: false)
    uv run python scripts/apply_golden_review.py   # drop / fix, then verified: true

Keeping the decisions in a file (not hand-edited JSON) makes the reviewed set
reproducible and shows exactly what the review changed.
"""

import json

from investigator.config import PROJECT_ROOT

GOLDEN = PROJECT_ROOT / "eval" / "golden"


def main() -> None:
    decisions = json.loads((GOLDEN / "review_decisions.json").read_text(encoding="utf-8"))
    path = GOLDEN / "golden.jsonl"
    items = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    unknown = (set(decisions["drop"]) | set(decisions["fix"])) - {i["id"] for i in items}
    if unknown:
        raise SystemExit(f"Review mentions unknown IDs: {sorted(unknown)}")

    kept = []
    for item in items:
        if item["id"] in decisions["drop"]:
            continue
        item |= decisions["fix"].get(item["id"], {})
        item["verified"] = True
        kept.append(item)

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for item in kept:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"{len(items)} drafted -> {len(kept)} verified ({len(decisions['drop'])} dropped, "
          f"{len(decisions['fix'])} fixed)")  # fmt: skip


if __name__ == "__main__":
    main()
