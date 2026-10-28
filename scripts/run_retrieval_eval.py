"""Run a grid of retrieval configurations from eval/configs/retrieval_grid.yaml.

Usage:
    uv run python scripts/run_retrieval_eval.py --grid stages --split test --n 500 \
        --qdrant-url http://localhost:6333

Writes eval/results/retrieval_<split>_<grid>.json (summaries), .md (table) and
_questions.jsonl (one row per question and config, for failure analysis).
Tune on --split dev; report --split test.
"""

import argparse
import json
import subprocess
from datetime import UTC, datetime

import yaml
from qdrant_client import QdrantClient

from investigator.config import PROJECT_ROOT, load_config, load_secrets
from investigator.evaluation.retrieval_eval import (
    CachedQueryEmbedder,
    CachedReranker,
    apply_overrides,
    evaluate_question,
    summarize,
)
from investigator.index.embeddings import make_openai_embedder
from investigator.index.sparse import BM25Encoder
from investigator.retrieval.local_models import load_local_models
from investigator.retrieval.rerank import CrossEncoderReranker
from investigator.retrieval.search import HybridRetriever

RESULTS_DIR = PROJECT_ROOT / "eval" / "results"
TABLE_COLUMNS = ["recall@2", "recall@5", "recall@10", "full@2", "full@5", "full@10", "rr",
                 "sent_recall@5", "context_words@10", "latency_ms"]  # fmt: skip


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", required=True)
    parser.add_argument("--split", choices=["dev", "test"], required=True)
    parser.add_argument("--n", type=int, default=500)
    parser.add_argument("--qdrant-url", default="http://localhost:6333")
    args = parser.parse_args()

    cfg, secrets = load_config(), load_secrets()
    grid = yaml.safe_load((PROJECT_ROOT / "eval/configs/retrieval_grid.yaml").read_text())[
        args.grid
    ]
    with open(PROJECT_ROOT / "data" / "gold.jsonl", encoding="utf-8") as f:
        questions = [q for q in map(json.loads, f) if q["split"] == args.split][: args.n]

    client = QdrantClient(url=args.qdrant_url, timeout=60)
    local = load_local_models(cfg.local_models.model_copy(update={"threads": None}))
    sparse = BM25Encoder(local.sparse)
    reranker = CachedReranker(
        CrossEncoderReranker(local.reranker, cfg.local_models.rerank_batch_size),
        cfg.local_models.reranker,
        PROJECT_ROOT / ".cache" / "rerank_scores.sqlite",
    )
    embedders: dict[str, CachedQueryEmbedder] = {}

    def embedder(name: str) -> CachedQueryEmbedder:
        """name: "production" or "comparison" (see config embeddings)."""
        if name not in embedders:
            inner = make_openai_embedder(secrets, cfg.embeddings, comparison=name == "comparison")
            embedders[name] = CachedQueryEmbedder(inner)
        return embedders[name]

    results, all_rows = {}, []
    for entry in grid:
        rcfg = apply_overrides(cfg.retrieval, entry["overrides"])
        retriever = HybridRetriever(
            client, entry["index"], rcfg, embedder(entry["embedder"]), sparse, reranker
        )
        rows = [evaluate_question(retriever, q) for q in questions]
        summary = summarize(rows)
        results[entry["name"]] = {"entry": entry, "config": rcfg.model_dump(), "summary": summary}
        all_rows += [{"config": entry["name"], **r} for r in rows]
        s = summary["all"]
        print(
            f"{entry['name']:30} R@5={s['recall@5']:.3f} Full@5={s['full@5']:.3f} "
            f"Full@10={s['full@10']:.3f} MRR={s['rr']:.3f} {s['latency_ms']:.0f}ms",
            flush=True,
        )

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
    meta = {
        "grid": args.grid,
        "split": args.split,
        "n_questions": len(questions),
        "date": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": commit.stdout.strip(),
        # Latency columns include reranker cache hits; this is the real model cost.
        "rerank_ms_per_pair": reranker.ms_per_pair(),
        "rerank_cache": {"hits": reranker.hits, "misses": reranker.misses},
        "dataset_manifest": json.loads((PROJECT_ROOT / "data/manifest.json").read_text()),
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stem = RESULTS_DIR / f"retrieval_{args.split}_{args.grid}"
    stem.with_suffix(".json").write_text(json.dumps({"meta": meta, "results": results}, indent=2))
    with open(f"{stem}_questions.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for row in all_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    stem.with_suffix(".md").write_text(markdown_table(meta, results), encoding="utf-8")


def markdown_table(meta: dict, results: dict) -> str:
    lines = [
        f"# Retrieval: {meta['grid']} ({meta['split']} split, {meta['n_questions']} questions)",
        "",
        f"Commit `{meta['git_commit']}`, {meta['date']}. Metrics over the top-K chunks.",
        "",
        f"Reranker cost: {meta['rerank_ms_per_pair'] or 0:.1f} ms per scored pair on my laptop "
        "CPU. Latency columns include reranker cache hits, so they understate the real cost.",
        "",
        "| config | " + " | ".join(TABLE_COLUMNS) + " |",
        "|---" * (len(TABLE_COLUMNS) + 1) + "|",
    ]
    for name, r in results.items():
        s = r["summary"]["all"]
        cells = [
            f"{s[c]:.3f}" if s[c] is not None and s[c] < 10 else f"{s[c]:.0f}"
            for c in TABLE_COLUMNS
        ]
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "By question type (full@5):",
        "",
        "| config | bridge | comparison |",
        "|---|---|---|",
    ]
    for name, r in results.items():
        bridge, comp = r["summary"].get("bridge", {}), r["summary"].get("comparison", {})
        lines.append(f"| {name} | {bridge.get('full@5', 0):.3f} | {comp.get('full@5', 0):.3f} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
