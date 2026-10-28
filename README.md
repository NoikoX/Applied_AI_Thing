# AI Investigation Engine

[![CI](https://github.com/NoikoX/Applied_AI_Internship/actions/workflows/ci.yml/badge.svg)](https://github.com/NoikoX/Applied_AI_Internship/actions/workflows/ci.yml)

Question answering over a large document collection that **links facts across documents**, **cites every claim**, **says when sources disagree**, and **refuses when the documents do not contain the answer**. Built for the Upgaming Applied AI task.

**Live demo:** https://applied-ai-internship.onrender.com (free tier: the first request after 15 idle minutes waits for a cold start) · **API docs:** `/docs`

| Document | What it covers |
|---|---|
| [docs/DECISIONS.md](docs/DECISIONS.md) | every design decision: options considered, choice, trade-offs, measured results |
| [docs/EVALUATION_REPORT.md](docs/EVALUATION_REPORT.md) | evaluation method, results, failure analysis, improvements |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | deployment architecture, free-tier limits, memory, costs, runbook |
| [docs/AI_USAGE.md](docs/AI_USAGE.md) | which AI tools were used, how, and what I did myself |

## What it does

Ask *"Which Emmett's Mark actor also played in the HBO series The Wire?"* and the system plans two steps (who is in Emmett's Mark; which of them was in The Wire), searches for each, checks whether the evidence covers both, searches again if not, and answers **"John Doman"** with each claim linked to the paragraph that states it. Ask about something the documents do not contain and it says so instead of guessing; give it two sources that disagree and it reports both.

**Corpus:** 46,172 Wikipedia paragraphs from HotpotQA (5,000 seeded questions), plus any PDF, DOCX, HTML, Markdown or text file a user uploads.

## Architecture

```
Browser ─► FastAPI (REST API + static page) ─► service layer (validation, limits, permissions)
              │
              ├─ Agent (LangGraph): plan → search (tool call) → grade → search again? → extract claims → answer
              ├─ Baseline: search → answer
              │      both end in code checks: citations must point to shown passages; refuse if evidence is weak
              ├─ Hybrid retriever: OpenAI dense + BM25 sparse in Qdrant, hand-written fusion and ranking
              └─ LLM gateway: cache, rate limits, retry/backoff, fallback, cost log
                     Gemini 3.5/3.1 Flash-Lite (free tier) ─ fallback gpt-5-mini
Qdrant Cloud: chunks + document registry          GitHub Actions: CI on every push, daily keep-alive
```

| Layer | Files | Notes |
|---|---|---|
| Ingestion | `ingestion/loaders.py`, `chunking.py`, `dedup.py` | 5 formats with metadata; 3 chunking strategies (paragraph, sentence window, recursive); exact + near-duplicate detection that keeps near-copies whose facts differ |
| Index | `index/registry.py`, `qdrant_store.py` | add / update / delete with versioned, idempotent writes; collections remember their embedding model |
| Retrieval | `retrieval/fusion.py`, `ranking.py`, `search.py` | **hand-written** RRF and weighted fusion, coverage-aware selection (MMR + sub-question coverage), cross-encoder reranking |
| LLM | `llm/gateway.py`, `retry.py`, `ratelimit.py`, `errors.py` | **hand-written** error classification (retry / quota / fatal), backoff with jitter, per-model rate limits, SQLite cache |
| RAG | `rag/baseline.py`, `citations.py`, `sufficiency.py` | structured answers with source labels; citation verification and refusal rules in code |
| Agent | `agent/graph.py`, `nodes.py`, `contradiction.py` | LangGraph state machine; nodes are plain functions; contradictions detected in code from extracted claims |
| Evaluation | `evaluation/*`, `scripts/run_*_eval.py` | **hand-written** metrics, golden set, LLM judge, record/replay prompt regression tests |
| API / UI | `api/*`, `ui/static/index.html` | REST endpoints, per-visitor and daily limits, admin token for corpus deletes |

## Results (details in the evaluation report)

| | |
|---|---|
| Retrieval, 500 test questions | `text-embedding-3-large` + weighted hybrid: Recall@5 **0.845**, both gold paragraphs in top 10 **0.834**, MRR **0.942** |
| Answers, 42 hand-verified golden questions | baseline + Gemini **39/42 correct**: all unanswerable questions refused, all prompt injections resisted, 4/6 contradictions flagged |
| Model comparison | same pipeline: Gemini Flash-Lite 0.93 · gpt-5-mini 0.79–0.81 · gpt-5-nano 0.48–0.55 |
| Main failure | the paragraph about an entity the question never names is not retrieved; the agent's second search round targets exactly this |

## Run it locally

Requirements: Python 3.12, [uv](https://docs.astral.sh/uv/), Docker (for a local Qdrant), API keys for Gemini (free) and OpenAI.

```bash
uv sync
cp .env.example .env                         # fill in the five keys
uv run pytest -q                             # 312 offline tests (no API calls)
```

Build the data and a local index:

```bash
docker run -d --name qdrant-eval -p 6333:6333 -v qdrant-eval-storage:/qdrant/storage qdrant/qdrant
uv run --group data python scripts/build_dataset.py
uv run python scripts/index_corpus.py --strategy paragraph --embedder production --index-name paragraph__large --qdrant-url http://localhost:6333
```

Serve the app (uses the Qdrant from `QDRANT_URL`; `app.index_name` in `config/config.yaml` picks the collection):

```bash
uv run uvicorn investigator.api.main:build_app --factory --port 8000
```

Evaluate:

```bash
uv run python scripts/run_retrieval_eval.py --grid embeddings --split test --n 500
uv run python scripts/build_golden_index.py
uv run python scripts/run_answer_eval.py --system agent --generator gemini
```

## Configuration and secrets

- `config/config.yaml`: every model name, threshold and limit lives here, not in code; `config/pricing.yaml`: token prices for cost logging.
- Secrets come only from the environment: `.env` locally (git-ignored, template in `.env.example`), Render environment variables in production. The app stops at startup with a clear message if one is missing.

## Main technical choices (why, in one line each)

- **Qdrant** for dense + sparse vectors in one place, with fusion done in my own code rather than Qdrant's built-in.
- **OpenAI `text-embedding-3-large`** chosen by measurement (+10 points vs `-small`) at the same vector size and memory.
- **Weighted fusion over RRF**, tuned on dev: it lets dense search overrule weak keyword matches.
- **Gemini Flash-Lite** as the generator: free, and in evaluation the most reliable at refusing and at using only the documents.
- **Code decides what must be reliable** (when to search again, citation validity, refusal, contradictions); the LLM does language work.
- **Static HTML page instead of Gradio** and **no reranker in the live demo**: both needed to fit Render's free 512 MB (measured: 206 MB idle).

## Repository layout

```
src/investigator/   application code (see the architecture table)
scripts/            dataset build, indexing, evaluations, golden set, cloud copy
config/             config.yaml, pricing.yaml
eval/               golden set, synthetic documents, evaluation configs and results
tests/              312 unit tests + replay cassette for prompt regression
docs/               decisions, evaluation report, deployment, AI usage
```
