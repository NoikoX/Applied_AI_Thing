"""Evaluate answer quality on the golden set (local Qdrant with the golden index).

    uv run python scripts/run_answer_eval.py --system agent --generator gemini
    uv run python scripts/run_answer_eval.py --system baseline --generator openai

--generator gemini uses the configured models; openai runs the planner, answer
and grader roles on the fallback model (gpt-5-nano) for the LLM comparison.
Writes eval/results/answers_<system>_<generator>.json, .md and _questions.jsonl.
Re-runs are cheap: LLM responses are cached on disk.
"""

import argparse
import json
import subprocess
from datetime import UTC, datetime

from investigator.config import PROJECT_ROOT
from investigator.evaluation.answer_eval import evaluate_item, summarize
from investigator.evaluation.judge import JUDGE_PROMPT_VERSION
from investigator.evaluation.systems import make_parts, make_system
from investigator.rag.prompts import PROMPT_VERSION

RESULTS = PROJECT_ROOT / "eval" / "results"
COLUMNS = ["correct", "status_correct", "contains", "f1", "judge_correct", "supported_claims",
           "evidence_recall", "citation_precision", "citation_recall", "llm_calls",
           "latency_ms"]  # fmt: skip


def build_system(name: str, generator: str, index: str):
    gateway, retriever, judge_gateway, llm_cfg = make_parts(generator, index)
    return make_system(name, gateway, retriever), judge_gateway, llm_cfg


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system", choices=["baseline", "agent"], required=True)
    parser.add_argument("--generator", choices=["gemini", "openai"], default="gemini")
    parser.add_argument("--index", default="golden__large")
    parser.add_argument("--ids", help="comma-separated golden IDs, for a quick partial run")
    args = parser.parse_args()

    golden = (PROJECT_ROOT / "eval/golden/golden.jsonl").read_text(encoding="utf-8")
    items = [json.loads(line) for line in golden.splitlines()]
    if args.ids:
        wanted = set(args.ids.split(","))
        items = [i for i in items if i["id"] in wanted]
    system, judge_gateway, llm_cfg = build_system(args.system, args.generator, args.index)

    rows = []
    for n, item in enumerate(items, start=1):
        row = evaluate_item(system, item, judge_gateway)
        rows.append(row)
        print(
            f"{n}/{len(items)} {item['id']} {item['category']:13} {row['status']:22} "
            f"correct={row['correct']} {row['latency_ms']:.0f}ms",
            flush=True,
        )

    summary = summarize(rows)
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
    meta = {
        "system": args.system,
        "generator": args.generator,
        "models": {r: getattr(llm_cfg, r).name for r in ("planner", "answer", "grader", "judge")},
        "index": args.index,
        "n_questions": len(items),
        "prompt_versions": [PROMPT_VERSION, JUDGE_PROMPT_VERSION],
        "date": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": commit.stdout.strip(),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    suffix = "_partial" if args.ids else ""
    stem = RESULTS / f"answers_{args.system}_{args.generator}{suffix}"
    stem.with_suffix(".json").write_text(json.dumps({"meta": meta, "summary": summary}, indent=2))
    with open(f"{stem}_questions.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    stem.with_suffix(".md").write_text(table(meta, summary), encoding="utf-8")
    print(table(meta, summary))


def table(meta: dict, summary: dict) -> str:
    def cell(v):
        return "–" if v is None else (f"{v:.3f}" if v < 10 else f"{v:.0f}")

    title = f"{meta['system']} / {meta['generator']} ({meta['n_questions']} golden questions)"
    lines = [
        f"# Answers: {title}",
        "",
        f"Models {meta['models']}, index `{meta['index']}`, commit `{meta['git_commit']}`.",
        "",
        "| slice | n | " + " | ".join(COLUMNS) + " |",
        "|---" * (len(COLUMNS) + 2) + "|",
    ]
    for name, block in summary.items():
        if name == "totals":
            continue
        lines.append(
            f"| {name} | {block['n']} | " + " | ".join(cell(block[c]) for c in COLUMNS) + " |"
        )
    a, t = summary["all"], summary["totals"]
    lines += [
        "",
        f"Refusal precision {cell(a['refusal_precision'])}, "
        f"recall {cell(a['refusal_recall'])} "
        f"({a['refused']} refused, {a['should_refuse']} should be).",
        f"Totals: {t['llm_calls']} LLM calls, {t['input_tokens']} input / "
        f"{t['output_tokens']} output tokens, ${t['cost_usd']} generation + "
        f"${t['judge_cost_usd']} judge; {t['answers_using_fallback']} answers used the fallback.",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
