# AI Usage Report

> **Draft.** Sections marked ✍️ must be completed by me (the author) in my own words before submission. The detailed, milestone-by-milestone record is in [ai_usage_log.md](ai_usage_log.md).

## Tools

| Tool | Used for |
|---|---|
| Claude Code (Claude Opus 5.5), desktop app | Planning, writing most of the code and tests, running scripts and evaluations, checking free-tier limits on the web, drafting documentation |
| ✍️ *any other tools (e.g. ChatGPT, IDE completion)* | ✍️ |

## How the work was split

**I decided** (recorded in the log as my choices):
- Dataset scope: started at 3,000 HotpotQA questions, then raised it to 5,000.
- Hosting on Render's free tier (with Oracle as the planned fallback), Qdrant Cloud, Gemini free tier as the main generator, OpenAI for embeddings.
- Dropping the slow local embedding model (bge) in favour of comparing `text-embedding-3-small` vs `-large`; switching production to `-large` after the evaluation.
- Accepting a faster reranker evaluation path (score cache) and live progress views for long runs.
- Reviewing the golden set: dropped G04 (wrong source answer) and G45 (duplicate fact), fixed G40.
- Moving slow Gemini evaluation runs to OpenAI models for the comparison, and moving the fallback model from gpt-5-nano to gpt-5-mini.
- The memory fix for the 512 MB host: replace Gradio with a plain page, load parsers lazily, run the demo without the reranker.
- Setting up accounts and keys myself (Qdrant, Render, GitHub, Gemini, OpenAI billing) and approving every push and deploy.

**The AI did**: proposed options with trade-offs for each decision, wrote the code and tests milestone by milestone, ran indexing and evaluations, measured memory and costs, and drafted the documents. Every milestone ended with a passing test suite and a commit I approved.

## How AI output was checked

- **Tests for every change:** 312 offline unit tests (fakes for the LLM, embeddings and Qdrant), run in CI on every push; hand-computed expected values for fusion, ranking and all metrics.
- **Live checks against the real services** after each component: OpenAI, Gemini, Qdrant Cloud, and the deployed site.
- **Measurement before claims:** memory in a 512 MB container, latency, real costs from the call log, confidence intervals on the evaluation.

Problems found this way (each fixed and covered by a test or recorded in DECISIONS.md):

| Found | Problem | Fix |
|---|---|---|
| CI on Linux | peak-memory metric could be below current memory (`ru_maxrss` updates lazily) | report max(peak, current) |
| live smoke test | uploaded files were chunked with the corpus strategy | uploads always use the upload strategy |
| live smoke test | OpenAI billing inactive; the SDK retried a non-recoverable 429 five times | error classification: quota errors are never retried |
| live agent run | "actor in Emmett's Mark / The Wire" flagged as a contradiction | conflicts only on single-valued properties |
| building the golden set | near-duplicate dedup would have hidden a contradicting source | near-duplicate only if numbers and names also match |
| the evaluation itself | golden question G20 was answerable after all (hyphenated spelling) | punctuation-blind check; G20 dropped |
| config change | two settings of the same model shared one LLM client | clients keyed by the full model spec |
| 512 MB container test | the full app was killed for memory on the first question | reranker batch size, no Gradio, no reranker in the demo |
| evaluation numbers | `llm_calls` ignored cached calls | count all calls, uncached separately |

## ✍️ What I changed or did independently

*Write here, in your own words:* code you rewrote or simplified by hand, parts you re-derived or tested yourself (e.g. recomputing the fusion or metric examples by hand), decisions where you overruled a suggestion, anything you built without AI.

## ✍️ What I learned / could explain without AI

*Write here:* the parts you can walk through in the interview, e.g. the request path, hybrid fusion, the ranking formula, the refusal rules, the gateway's retry policy, the evaluation metrics.
