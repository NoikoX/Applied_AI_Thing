# AI Usage Report

The detailed, milestone-by-milestone record is in [ai_usage_log.md](ai_usage_log.md).

## Tools

| Tool | Used for |
|---|---|
| Claude Code (Claude Opus 5.5), desktop app | Planning, writing most of the code and tests, running scripts and evaluations, checking free-tier limits on the web, drafting documentation |

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

## What I did myself

I wrote very little of the code by hand; my work was directing, deciding and checking. I set the goals and constraints at the start ($0 infrastructure, free-tier hosting, an honest evaluation over complexity, a list of components that had to stay hand-written so I could explain them), and I made the calls whenever there was a real trade-off: the dataset size, Render over the alternatives, OpenAI embeddings and later switching to `-large` once the numbers showed it, dropping local bge when it was too slow, moving slow Gemini runs to OpenAI models, and how to fit the app into 512 MB. Where I disagreed with the default path I changed it, for example asking for a faster reranker path and a cheaper way to run evaluations instead of waiting hours.

I also did the parts that needed a person: creating and configuring Qdrant Cloud, Render, GitHub and the API keys, re-activating OpenAI billing when it turned out to be inactive, reading the real rate limits in AI Studio, reviewing the drafted golden questions (I dropped two and fixed one), and testing the live app myself and checking its answers against the cited sources. Every push and deployment went through only after I approved it.

## What I learned

The biggest lessons came from things that went wrong and were measured rather than guessed: the app that worked locally was killed for memory on the free host until we found the reranker's batch size; a deduplication rule that looked sensible would have hidden exactly the contradicting sources the task asks to detect; the cheapest model refused almost everything; and the evaluation itself found a wrong label in my own golden set. I learned to treat the evaluation as the centre of the project, to separate retrieval failures from answering failures, and to report what did not work as plainly as what did.
