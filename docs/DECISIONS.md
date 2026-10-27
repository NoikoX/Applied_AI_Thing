# Design Decisions — AI Investigation Engine

Status: accepted 2026-10-27. Source of truth for requirements: `docs/applied_ai_investigation_engine_task.md`.
Each decision lists options, the choice, why, trade-offs, and how I would defend it in the interview.

## 0. Verified facts (checked 2026-10-27)

| Service | Fact | Confidence |
|---|---|---|
| Gemini API | Free-tier limits are per account and shown only in AI Studio; the official docs page lists no free numbers. Recommended models for new projects: `gemini-3.5-flash-lite`, `gemini-3.8-flash`. 2.5 models are restricted to previous users. | Model list official. **Verified in my AI Studio account (2026-10-27):** free tier per model: `gemini-3.5-flash-lite` and `gemini-3.1-flash-lite` = 15 RPM, 250K TPM, 500 RPD each; `gemini-3.8-flash` = 5 RPM, 20 RPD (third-party sites said 10 RPM for Flash-Lite). Limits are per project and per model. |
| Qdrant Cloud | Free cluster: 0.5 vCPU, 1 GB RAM, 4 GB disk, single node. Suspended after 1 week unused, deleted after 4 weeks if not reactivated. | Official docs. |
| Hugging Face Spaces | Docker/Gradio Spaces now require PRO. Free accounts: static Spaces, or up to 2 Gradio Spaces on ZeroGPU. | Official docs; start date (Jul vs Aug 2026) conflicts between secondary sources. |
| Render free | Spins down after 15 min idle (~1 min cold start), 750 instance-hours/month, ephemeral filesystem, no persistent disk. | Official docs. RAM **512 MB is unverified** (from a Render article, not the docs) → measured in milestone 1. |
| Oracle Always Free | Arm A1 reduced to 2 OCPU / 12 GB (was 4 / 24) around June 2026. Card required. | Secondary sources. |
| OpenAI | `text-embedding-3-small` $0.02 / 1M tokens; `gpt-5-nano` $0.05 in / $0.40 out; `gpt-5-mini` $0.25 / $2.00. | Official pricing page. |

All model names below are **config values**, not code. They may change; `config/config.yaml` is the only place they live.

---

## D1. Hosting & deployment architecture

| Option | Pros | Cons |
|---|---|---|
| **Render free, one Docker container: FastAPI + Gradio mounted (`gr.mount_gradio_app`)** | No card, public URL, one process serves REST API and UI | ~512 MB RAM (unverified), cold starts, ephemeral disk |
| Oracle Always Free VM | 12 GB RAM, never sleeps, real disk | Card required, I operate the VM (TLS, updates, Docker) |
| HF Spaces Docker | Previously the default for ML demos | No longer free |
| Streamlit Cloud UI + Render API | More RAM for UI | Two hosts, two sleep policies |

**Chosen:** Render free. **Fallback:** Oracle Always Free if milestone-1 memory measurement fails (target: peak RSS < 400 MB under a query).

**Why:** With OpenAI embeddings, the server only holds BM25 tokenization, a small ONNX cross-encoder, and the app — no PyTorch. All state lives in Qdrant Cloud, so the ephemeral disk does not matter.

**Architecture:**
```
Browser ──> Render container
              ├─ FastAPI  (/ask, /documents CRUD, /health)
              ├─ Gradio UI mounted at /
              ├─ fastembed: Qdrant/bm25 (sparse), MiniLM cross-encoder (ONNX)
              └─ LLMGateway ──> Gemini (primary) / OpenAI (fallback, judge)
                     │                └─> OpenAI embeddings (query + ingest)
                     └─> Qdrant Cloud (chunks collection + documents registry)
GitHub Actions: CI (offline tests) · daily keep-alive /health/deep · manual live eval
```

**Memory measured (M1, 2026-10-27):** Docker container capped at 512 MB / 0.5 CPU, after model warm-up (BM25 + 30-candidate rerank) and a UI page load: 290 MiB container memory (process RSS 350 MB), no OOM. Under the 400 MB target → Render confirmed. Image size 1.53 GB, models baked in.

**Health checks:** `/health` is liveness only (no external calls; Render's health check). `/health/deep` makes a real Qdrant call and returns 503 if it fails.

**Keep-alive:** a daily GitHub Actions cron calls `/health/deep`, so Qdrant sees real traffic. This prevents the 1-week Qdrant pause. I do not keep Render awake artificially; the cold start is documented. (GitHub disables scheduled workflows in inactive repos after a while — not re-verified; noted in README.)

**Secrets:** `.env` locally (gitignored), `.env.example` committed with empty values, Render environment variables in production, GitHub Secrets for the live-eval workflow. Settings are loaded with `pydantic-settings`; the app fails fast if a required key is missing.

**Demo protection:**
- `slowapi` per-IP limits (e.g. 5 `/ask` per minute, 30 per day).
- A global daily LLM-call budget; when exhausted, `/ask` returns a clear "demo quota reached" message.
- Answer cache for repeated questions.
- Visitor uploads: max 5 MB, tagged `source=upload`; visitors may delete only uploads. Updating/deleting corpus documents requires an `ADMIN_TOKEN` header.

**Trade-offs:** cold starts hurt the first impression; a single small instance means modest latency (rerank on ~0.5 vCPU).

**Interview defense:** "The constraint was $0 and persistence. I pushed all state into Qdrant Cloud so the app container is stateless and can restart anywhere. I chose OpenAI embeddings partly to keep PyTorch out of a 512 MB container, measured memory before committing, and had Oracle as a pre-planned fallback."

---

## D2. LLM layer: one interface, fallback, 429s, caching, cost logging

| Option | Pros | Cons |
|---|---|---|
| **Own `LLMGateway` over LangChain chat models** (`langchain-google-genai`, `langchain-openai`) | Cross-cutting policy (cache, retry, fallback, cost) written by me in one place; LangChain gives uniform tool calling (`bind_tools`) and structured output (`with_structured_output`); plays well with LangGraph | One more abstraction layer |
| LiteLLM | One API for many providers | I'd be defending its retry/fallback behaviour, not mine |
| Raw provider SDKs | Fully transparent | Tool calling and structured output written twice |

**Chosen:** own gateway over LangChain chat models.

**Roles in config:** `planner`, `answer` → `gemini-3.5-flash-lite`; `grader` (grading + claim extraction, the highest-volume role) → `gemini-3.1-flash-lite`, because free limits are per model, so this doubles the free daily budget to ~1,000 calls; `fallback` → `gpt-5-nano`; `judge` (eval only) → OpenAI (`gpt-5-mini` candidate).

**Call path:** `invoke(role, messages, schema=None, tools=None)`
1. Cache lookup — SQLite table, key = SHA-256 of (provider, model, messages, params, schema version). Temperature 0. Makes evaluation repeatable and cheap to re-run.
2. Client-side rate limiter (token bucket per model, RPM from config).
3. Call primary. On 429/5xx/timeout: exponential backoff with jitter (`tenacity`), honouring the provider's retry delay when given; max N attempts.
4. Persistent failure → fallback provider. Response records which provider answered.
5. Log one JSONL line per call: role, provider, model, input/output tokens, latency, cost (from `config/pricing.yaml`), cache hit.
6. Typed errors (`LLMQuotaExceeded`, `LLMUnavailable`, `LLMBadOutput`) so the API returns a clean message instead of a stack trace.

**Trade-offs:** a fallback model behaves differently → evaluation records the answering provider and fallback runs are reported separately.

**Interview defense:** "Free tiers fail with 429s, so quota handling is a first-class concern: limit before calling, back off when told, fall back when stuck, and cache so evaluation never pays twice. Every call is logged with tokens and cost, which is how I report LLM costs."

---

## D3. Vector database & hybrid search

| Option | Hybrid approach | Cons |
|---|---|---|
| **Qdrant Cloud, named dense + sparse vectors** | Dense = OpenAI; sparse = BM25 (`Qdrant/bm25` via fastembed, IDF modifier on server). Two separate queries, **fusion written by me in Python** | 1 GB RAM free tier |
| Neon Postgres + pgvector + tsvector | Familiar SQL | Weaker keyword ranking than BM25 |
| Chroma + in-memory `rank_bm25` | Simple | BM25 index rebuilt on every restart |

**Chosen:** Qdrant Cloud. I deliberately do **not** use Qdrant's built-in fusion. Production fusion after M6: **weighted, α = 0.5** (beat RRF on dev and test; α tuned on dev).

**Safety check:** both indexing and search refuse a collection whose stored embedding model differs from the configured one, because mismatched vectors return plausible but meaningless results without any error. Local experiment collections are named after their model (`paragraph__large`, `paragraph__small`, `sentence_window__small`); the deployed app uses `paragraph`.

**Fusion methods (hand-written, both evaluated):**
- **RRF** (reciprocal rank fusion): `score(d) = Σ_lists 1 / (k + rank(d))`, k = 60. Uses ranks only, so no score calibration between dense cosine and BM25 is needed.
- **Weighted score fusion:** min-max normalize each list, then `α·dense + (1−α)·sparse`.

**Experiments** run against local Qdrant (`QdrantClient(path=...)`, in-process); only the winning configuration is deployed to Qdrant Cloud.

**RAM estimate:** 30k × 1536 floats × 4 B ≈ 184 MB for paragraph chunks; sentence windows roughly double that. Fits one configuration in 1 GB.

**Interview defense:** "Dense search catches paraphrases; BM25 catches exact names and numbers, which HotpotQA is full of. RRF combines them without needing comparable scores. I wrote the fusion myself and compared it to weighted fusion."

---

## D4. Embeddings & reranker

| Option | Notes |
|---|---|
| **`text-embedding-3-small` (OpenAI)** | No local model RAM, fast batched ingest, ~$0.08 for the corpus; supports a `dimensions` parameter |
| `BAAI/bge-small-en-v1.5` (local, fastembed ONNX) | Free, 384-d, 67 MB; needs a query prefix (fastembed handles it) |
| `gemini-embedding-001` | Free but daily request limits make full ingest slow |

**Chosen:** `text-embedding-3-small` in production at first; **switched to `text-embedding-3-large` (1,536 dims) after M6**, where it beat `-small` by ~10 points Full@5 on both dev and test, at the same Qdrant RAM and ~$0.77 one-off indexing cost. `-small` is now the comparison model. **Comparison (bonus):** originally `bge-small-en-v1.5` offline; changed in M6 to `text-embedding-3-large` at the same 1,536 dimensions, because bge ran at ~11–15 texts/s on my laptop CPU (~50–70 min for the corpus) while the API model indexed in ~18 min for ~$0.77. Same vector size means only the model differs. Results: see "M6 retrieval results" under D10.

**Reranker:** cross-encoder `Xenova/ms-marco-MiniLM-L-6-v2` via fastembed (ONNX, ~80 MB). A cross-encoder reads (query, passage) together → more accurate than vector similarity, but too slow for more than ~30 candidates, so it only rescores the fused top 30.

**Trade-offs:** every query depends on OpenAI. Mitigation: retry, then degrade to BM25-only search with a visible warning. Changing embedding models requires re-indexing; model name and dimension are stored in collection metadata and checked at startup.

**Library roles:** `openai` — embeddings API; `fastembed` — ONNX runtime for BM25 tokenization and the cross-encoder, no PyTorch.

**Interview defense:** "API embeddings removed the heaviest dependency from a tiny server. I didn't just trust them: I compared them to an open local model on the same test set and report both."

---

## D5. Custom ranking component (hand-written)

**Coverage-aware selection** — a greedy extension of MMR (maximal marginal relevance) for multi-hop questions:

1. Hybrid fusion (D3) → top 30 candidates.
2. Cross-encoder score `ce` (normalized 0–1).
3. Greedy selection: repeatedly pick the candidate maximizing
   `w_ce·ce + w_rrf·rrf + w_cov·covers_new_subquery − λ·max_cos(candidate, selected) − β·[source already has 2 selected chunks]`
   until K chunks are selected or the best score falls below `τ`.

- `covers_new_subquery`: 1 if the candidate is among the top results for a sub-question not yet covered by selected chunks.
- The stop condition (`best score < τ`) is also an input to the insufficient-evidence decision (D9).

**Why:** bridge questions need two *different* paragraphs. Pure relevance ranking tends to return near-duplicates of the first hop.

**Tuning:** weights tuned on a dev split only (D7); the reported test split is never used for tuning. Start with λ and `w_cov` only; ablation table shows each term's contribution.

**Early sanity check (M5, not the evaluation):** 60 dev questions on a small index of only their own 600 paragraphs, real models, no sub-questions:

| Config | Recall@5 | Both gold in top 5 |
|---|---|---|
| dense | 0.883 | 0.767 |
| BM25 | 0.775 | 0.583 |
| hybrid RRF | 0.867 | 0.733 |
| hybrid weighted | 0.883 | 0.767 |
| hybrid + rerank | 0.858 | 0.717 |
| hybrid + rerank + coverage | 0.817 | 0.650 |

On this tiny, easy index neither reranking nor coverage helped, and without sub-questions the coverage term is inactive, so only the redundancy penalty acts (and it can push out the second gold paragraph, which is topically similar to the first). 60 questions is also within noise (one question = 0.017). The real comparison runs in M6 on the full 46k-paragraph index, and coverage is meant to be judged with the agent's sub-questions. Reranker cost measured on my laptop: ~1.7 s for 30 pairs with 1 thread, ~0.6 s with all threads; Render (0.5 vCPU) will be slower — to measure in M13.

**Options rejected:** plain cross-encoder top-K (no diversity, no hop coverage); learned-to-rank (needs training data and is harder to explain).

**Interview defense:** "I can derive every term. Relevance comes from the cross-encoder and fusion, diversity from MMR's redundancy penalty, and the coverage bonus is specific to multi-hop: it rewards evidence for the part of the question not yet answered. The ablation shows it earns its place."

---

## D6. Chunking

| Option | Unit | Role |
|---|---|---|
| **A. Paragraph = one chunk** | HotpotQA paragraph with title | Baseline |
| **B. Sentence window: 3 sentences, stride 2** | Overlapping sentence groups | Finer evidence; enables sentence-level evidence recall (HotpotQA marks supporting sentences) |
| C. Recursive 256-token splitter with overlap (LangChain `RecursiveCharacterTextSplitter`) | Fixed size | Used for uploaded long documents (PDF/DOCX/HTML) |

**Chosen:** compare **A vs B** on the dataset (the required comparison); C for uploads.

**Measured on the corpus (M3):** A = 46,172 chunks (median 77 words, max 1,378); B = 84,778 chunks (median 58 words, max 320). For uploads without sentence labels, B uses a hand-written regex sentence splitter (approximate: it also splits after abbreviations such as "Dr.").

**Trade-offs:** B doubles the point count and can split a fact across windows (overlap mitigates). A keeps context but dilutes the embedding for long paragraphs.

**Interview defense:** "HotpotQA's sentence-level gold labels let me measure what chunking actually changes: whether the supporting sentence is retrieved, not just the right article."

---

## D7. Dataset, sampling & reproducibility

| Option | Size |
|---|---|
| **HotpotQA distractor, train split, 3,000 questions, seed 42** | ~25–30k unique paragraphs |
| 6,000 questions | ~55–60k paragraphs (meets 50k at paragraph level) |
| Full validation split (7,405) | ~60–70k paragraphs |

**Chosen:** 5,000 questions from the train split (90,447), seed 42 (my decision; first built with 3,000, then raised). `n_questions` is a config parameter.

**Built (M2, 2026-10-27, dataset revision pinned in config):** 5,000 questions (4,032 bridge, 968 comparison; 2,500 dev / 2,500 test) → 49,653 paragraphs seen → **46,172 unique** after removing 3,481 exact duplicates; 1 out-of-range supporting-sentence label dropped. Average paragraph: 4.03 sentences, 87 words. Rebuilding gives byte-identical files (hashes in `data/manifest.json`).

**Against the ≥ 50,000 requirement:** 46,172 unique paragraphs, and **84,778 chunks** under chunking B (3-sentence windows, stride 2). If a reviewer counts unique paragraphs only, about 5,500 questions would cross 50k; that is a config change plus a few cents of embeddings.

**Build script outputs:**
- `data/corpus.jsonl` — unique paragraphs (dedup by normalized title+text hash), with source question IDs kept for traceability.
- `data/gold.jsonl` — 3,000 questions, answers, gold paragraph titles, supporting sentence indices, type (bridge/comparison), level. Never indexed.
- `data/manifest.json` — dataset name, HF revision, split, seed, counts, SHA-256 of each output file. Data files are gitignored; the manifest is committed.

**Splits:** the 3,000 questions are split (seeded) into **dev** (tuning) and **test** (reported retrieval metrics).

**Synthetic cases (later milestone):**
- *Unanswerable:* (a) take a real question and delete one gold paragraph via the document API — truly unanswerable, and exercises delete; (b) questions about entities absent from the corpus.
- *Contradictory:* copy a gold paragraph, change one fact (date/number/name), save as PDF, DOCX or Markdown with `synthetic=true`. Expected: system flags the conflict and cites both sources. Also demonstrates ≥ 3 file formats.
- Danluu post-mortems may be added later for an incident-investigation flavour.

**Interview defense:** "Fixed seed, pinned dataset revision, hashed outputs: anyone can rebuild the exact corpus. Gold answers are kept out of the index so evaluation can't leak."

---

## D8. Document processing, registry & dedup

**Formats:** PDF (`pypdf`), DOCX (`python-docx`), HTML (`beautifulsoup4`), Markdown/TXT, JSONL (corpus). Extracted metadata: title, source, format, page (PDF), author/created date where present, content hash, version, ingest time.

| Registry option | Pros | Cons |
|---|---|---|
| **Payload-only `documents` collection in Qdrant** | One service; survives restarts | No joins |
| Neon / Supabase Postgres | Relational | Second free service to keep alive |
| SQLite on host | Simplest | Lost on restart (ephemeral disk) |

**Chosen:** registry in Qdrant.

- **IDs:** corpus `doc_id = "hp_" + content hash`; upload `doc_id = "up_" + hash(lower-cased file name)`, so re-uploading a file with the same name is an update; `chunk_id = UUID5(fixed namespace, doc_id:chunk_index)` (Qdrant needs UUID or int IDs) → re-ingesting is idempotent.
- **Add:** hash check → chunk → embed → upsert chunks + registry entry.
- **Update:** upsert the new chunks with `version + 1` (deterministic IDs overwrite old chunks in place), then delete this document's chunks with a lower version. The document is never left with zero chunks, and a crash midway is fixed by re-running. An unchanged document (same content hash) is skipped without re-embedding.
- **Chunking per document type:** corpus paragraphs use the collection's strategy (the one under evaluation); uploads always use the upload strategy (C).
- **Collections:** `chunks_<strategy>` (named vectors `dense` + `bm25`, payload indexes on `doc_id` and `version`) and `docs_<strategy>` (registry, payload-only). The embedding model and dimension are stored in the collection metadata; startup refuses a collection built with another model.
- **Bulk corpus ingest:** one embedding request per 256 documents; skips the per-document duplicate lookups, which is safe because corpus IDs are content hashes.
- **Delete:** remove chunks and registry entry.
- **Dedup (hand-written):** exact — SHA-256 of normalized text, checked before indexing; near-duplicate — if a new chunk's top-1 dense neighbour has cosine > 0.95, store it as `duplicate_of` instead of indexing it again. Counts reported at ingest.

**Interview defense:** "Deterministic IDs make every write idempotent, so a crashed ingest can simply be rerun. Dedup is two-tier: cheap exact hashing first, an embedding check for near-copies second."

---

## D9. Agentic RAG with LangGraph

| Option | Notes |
|---|---|
| **Fixed graph: plan → retrieve (tool call) → grade → (loop ≤ 2) → contradiction check → answer → verify** | Every step inspectable and testable |
| Free-form ReAct agent | Less code, unpredictable cost, harder to explain |
| Single-shot RAG | Kept as **baseline configuration** for evaluation |

**Chosen:** fixed graph, evaluated against single-shot. State is a `TypedDict`; each node is a plain function `(state) -> partial update`.

| Node | What it does | Who decides |
|---|---|---|
| `plan` | Structured output (Pydantic): question type (single / bridge / comparison), sub-questions | LLM |
| `retrieve` | LLM calls the tool `search_documents(query, k)` via `bind_tools`; tool runs hybrid search + D5 ranking. For bridge questions, hop-2 query includes the entity found in hop 1 | LLM chooses queries; search is my code |
| `grade` | Per sub-question: supported? what is missing? Missing → back to `retrieve` with refined query (max 2 loops) | LLM, loop limit in code |
| `contradiction` | LLM extracts claims `(subject, attribute, value, chunk_id)`; **Python** normalizes and groups by (subject, attribute) and flags differing values | Hand-written |
| `answer` | Structured output: `answer`, `claims[{text, chunk_ids}]`, `status ∈ {answered, insufficient_evidence, contradictory}` | LLM |
| `verify` | **Python:** every cited ID exists in retrieved set; refuse if grader says missing, top rerank score < threshold, D5 stopped early, or a key claim lacks a citation | Hand-written |

**Library roles:** `langgraph` — state machine with conditional edges and loop control; `langchain-core` — messages, tool schema, structured output; `pydantic` — output schemas.

**Trade-offs:** ~4–6 LLM calls per question vs 1 for baseline → cost and latency measured and reported per configuration.

**Interview defense:** "The LLM does language tasks — planning, query writing, claim extraction. Decisions that must be reliable — whether citations are real, whether evidence is sufficient, whether claims conflict — are deterministic Python I can unit-test."

---

## D10. Evaluation (centerpiece)

**Layer 1 — retrieval at scale (no LLM, near-free):** ~500 test-split questions.
- **Recall@K** — share of gold paragraphs in top K (K = 5, 10, 20).
- **Full-support@K** — both gold paragraphs in top K (what multi-hop actually needs).
- **MRR** — mean of 1 / rank of the first gold paragraph.
- **Sentence-level evidence recall** — supporting sentences retrieved (chunking A vs B).
- Grid: dense / BM25 / hybrid-RRF / hybrid-weighted / + rerank / + coverage ranking × chunking A/B × embeddings OpenAI/bge.

**Layer 2 — golden set (≥ 45 questions, every one checked by me):**

| Category | Count |
|---|---|
| Simple (single paragraph) | 10 |
| Multi-hop bridge | 10 |
| Comparison (links two documents) | 8 |
| Unanswerable | 7 |
| Contradictory | 6 |
| Prompt injection (optional bonus) | 4 |

Metrics (all hand-written):
- **Answer correctness:** HotpotQA-style normalized exact match and token F1; plus LLM-judge semantic correctness.
- **Citation precision / recall** against gold paragraphs.
- **Grounding (hallucination check):** per claim, judge decides whether the cited chunk supports it → supported-claim rate.
- **Refusal precision / recall** on unanswerable; **contradiction detection rate** on contradictory.
- Cost, tokens, latency per question.

**Configurations compared:** single-shot vs agentic; Gemini vs `gpt-5-nano` as generator (bonus); retrieval grid above.

**Judge bias:** an OpenAI judge may favour the OpenAI generator. Mitigations: EM/F1 and citation metrics are primary; judge is secondary; I hand-check 20 judgments and report agreement.

**Prompt regression tests:**

| Option | Notes |
|---|---|
| **Offline in CI:** rendered-prompt snapshots, schema/parsing tests, replay of recorded LLM responses through the pipeline with metric thresholds | Deterministic, no secrets in CI |
| Live LLM calls in CI | Flaky, costly |

**Chosen:** offline suite on every push; live 10-question suite as a manual `workflow_dispatch` workflow using a repository secret.

**Interview defense:** "Two layers: cheap retrieval metrics on hundreds of questions for statistical signal, and a hand-checked golden set for behaviours a dataset can't test — refusing and flagging contradictions. Every metric is my own code with unit tests on hand-computed examples."

### M6 retrieval results (single-pass retrieval, no sub-questions)

Full index (46,172 paragraphs; 84,778 sentence windows) in a local Qdrant 1.20 (Docker), tuned on 200 dev questions, reported on 500 test questions. After these runs the local collections were renamed after their model (the test result files still show the old names `paragraph` = small, `paragraph__comparison` = large); re-running the dev embedding grid on the renamed copies moved numbers by at most 0.5 points, because Qdrant's HNSW search is approximate and the graph is rebuilt on copy. Metrics over the top-K chunks. Tables and per-question rows: `eval/results/retrieval_*`. "Full@K" = both gold paragraphs in the top K.

| Config (test, 500) | Recall@5 | Full@5 | Full@10 | MRR |
|---|---|---|---|---|
| BM25 | 0.728 | 0.502 | 0.664 | 0.874 |
| dense (small) | 0.787 | 0.608 | 0.726 | 0.908 |
| hybrid RRF (small) | 0.797 | 0.628 | 0.750 | 0.911 |
| hybrid weighted α=0.5 (small) | 0.822 | 0.668 | 0.762 | 0.923 |
| hybrid RRF + rerank (small) | 0.809 | 0.632 | 0.756 | 0.936 |
| dense (large) | 0.853 | 0.722 | 0.814 | 0.925 |
| **hybrid weighted (large)** | 0.845 | 0.712 | **0.834** | **0.942** |

Findings:
- **Embeddings:** `text-embedding-3-large` beats `-small` by ~5 points Recall@5 and ~10 points Full@5, on dev and test alike. Best on dev: large + weighted fusion (Full@5 0.720, Full@10 0.820, MRR 0.962). Same 1,536 dimensions, so the same Qdrant RAM; cost $0.13 vs $0.02 per 1M tokens, i.e. ~$0.77 vs ~$0.12 to index the corpus once, queries negligible.
- **Fusion:** weighted (α = 0.5, tuned on dev over 0.3–0.9) beats RRF. RRF lets BM25 pull in keyword matches that dense search correctly ranked low; this hurts comparison questions most (dense 0.946 → RRF 0.848 Full@5).
- **Reranker:** raises MRR (0.911 → 0.936) and Full@2, but not Full@5/10. It costs ~58 ms per pair on my laptop CPU (~1.7 s per question for 30 candidates); Render will be slower.
- **Coverage selection:** with λ = 0 and no sub-questions it is identical to top-k (the coverage bonus needs sub-questions; paragraph chunks never hit the 2-per-document cap). Dev tuning: λ 0.0 > 0.15 > 0.3, because a question's two gold paragraphs are often similar to each other. To be re-evaluated with the agent's sub-questions.
- **Chunking:** A (paragraph) beats B (sentence windows) on every metric (Full@5 0.632 vs 0.598 with rerank), with B also giving less context (600 vs 869 words in the top 10). HotpotQA paragraphs are already short (median 77 words), so splitting them only separates facts from their context. Caveat: compared at equal chunk count, not equal word budget.
- **Failure analysis** (hybrid weighted, small): 166 / 500 questions miss a gold paragraph in the top 5; 159 are bridge questions. In **143 of the 166 (86%) the missed paragraph is the bridge entity, which the question never names** (e.g. "the philosopher whose philosophy Harry Jaffa developed…" needs *Leo Strauss*). Single-pass retrieval cannot find it; a second retrieval hop that uses what the first paragraph says can. This is the main motivation for the agent (D9).

---

## D11. UI

| Option | Notes |
|---|---|
| **Gradio mounted inside FastAPI** | One process; tabs for Ask (answer + citations + evidence), Documents (upload/list/update/delete), Status |
| Streamlit | Separate process/host; reruns script per interaction |
| FastAPI + HTMX templates | Most control, most UI code |

**Chosen:** Gradio in FastAPI. The UI calls the same service layer as the REST API, so there is one code path to test.

---

## Hand-written by me (not delegated to libraries)

Hybrid fusion (RRF, weighted) · coverage-aware ranking · dedup · contradiction grouping · sufficiency/refusal rules · citation verification · LLM gateway policy (cache, limiter, retry, fallback, cost) · all evaluation metrics.

## Defaults I chose where questions were left open

- Visitor uploads allowed but sandboxed; corpus changes admin-only.
- Bonus scope: agentic RAG, embedding comparison, LLM comparison, caching/cost logging. Streaming and prompt-injection tests only if time allows.
