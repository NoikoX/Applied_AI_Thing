"""Build data/corpus.jsonl, data/gold.jsonl and data/manifest.json from HotpotQA.

Usage:
    uv run --group data python scripts/build_dataset.py
"""

import json
import platform

from datasets import load_dataset

from investigator.config import PROJECT_ROOT, load_config
from investigator.data.hotpotqa import build, sample_indices, sha256_file, write_jsonl

DATA_DIR = PROJECT_ROOT / "data"


def main() -> None:
    cfg = load_config().dataset
    ds = load_dataset(cfg.hf_name, cfg.hf_config, split=cfg.split, revision=cfg.hf_revision)
    indices = sample_indices(len(ds), cfg.n_questions, cfg.seed)
    result = build([ds[i] for i in indices], cfg.dev_fraction)

    DATA_DIR.mkdir(exist_ok=True)
    corpus_path, gold_path = DATA_DIR / "corpus.jsonl", DATA_DIR / "gold.jsonl"
    write_jsonl(corpus_path, result.corpus)
    write_jsonl(gold_path, result.gold)

    manifest = {
        "dataset": cfg.hf_name,
        "config": cfg.hf_config,
        "revision": cfg.hf_revision,
        "split": cfg.split,
        "split_size": len(ds),
        "seed": cfg.seed,
        "dev_fraction": cfg.dev_fraction,
        "python_version": platform.python_version(),  # random.sample is stable per version
        **result.stats,
        "sha256": {"corpus.jsonl": sha256_file(corpus_path), "gold.jsonl": sha256_file(gold_path)},
    }
    (DATA_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
