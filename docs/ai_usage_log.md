# AI Usage Log

Running log for the final AI Usage Report. Claude drafts an entry per milestone; I edit it and fill in "What I changed / verified myself".

| Date | Milestone | Tool | What the AI did | What I changed / verified myself |
|---|---|---|---|---|
| 2026-10-27 | Planning | Claude Code (Opus 5.5) | Checked free-tier limits on the web, compared options for each decision, drafted `docs/DECISIONS.md` and the milestone plan | Chose the dataset size (3,000 questions), hosting (Render), and OpenAI embeddings. _TODO: add notes_ |
| 2026-10-27 | M0 Scaffold | Claude Code (Opus 5.5) | Set up git, `pyproject.toml` (uv), config loader with tests, `.env.example`, CI workflow, `CLAUDE.md` | _TODO_ |
| 2026-10-27 | Between M0 and M1 | Claude Code (Opus 5.5) | Checked my keys with free model-list calls; after I read the AI Studio limits, moved the grader role to `gemini-3.1-flash-lite` for a second free quota | I created the Qdrant cluster, Render account, GitHub repo and API keys myself and read the rate limits in AI Studio. _TODO_ |
| 2026-10-27 | M1 Hosting spike | Claude Code (Opus 5.5) | FastAPI app with liveness/deep health checks, Gradio mounted at `/ui`, fastembed BM25 + reranker with warm-up, Dockerfile with models baked in, keep-alive workflow, tests with in-memory Qdrant; measured memory in a 512 MB Docker container | _TODO: review `api/main.py`, `api/health.py`, Dockerfile_ |
