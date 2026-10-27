# AI Investigation Engine

Requirements: `docs/applied_ai_investigation_engine_task.md`. Decisions: `docs/DECISIONS.md` (do not contradict it without asking).

## Commands
- Install: `uv sync`
- Tests: `uv run pytest -q` (offline; no network in unit tests)
- Lint: `uv run ruff check . && uv run ruff format --check .`

## Rules
- The owner must defend all code in an interview without AI. Prefer plain, readable code over clever code; small functions; no speculative abstractions.
- Hand-written components must stay hand-written: fusion, ranking, dedup, contradiction, sufficiency/refusal, citation verification, LLM gateway policy, all eval metrics. Never replace them with library calls.
- LangGraph nodes are plain functions `(state) -> dict`.
- Model names live only in `config/config.yaml`; prices in `config/pricing.yaml`.
- Secrets only via environment (`.env`, never committed). Update `.env.example` when adding a key.
- Every change comes with tests; use fakes for LLM, embeddings, and Qdrant (`:memory:`) in unit tests.
- Work milestone by milestone; finish with green pytest and one commit.
- After each milestone, append a draft entry to `docs/ai_usage_log.md` (what AI did, what to review); the owner edits it.
- Never tune weights or thresholds on the test split.
