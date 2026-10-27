# AI Investigation Engine

Multi-hop RAG over HotpotQA with hybrid search, citations, contradiction detection and an automated evaluation suite.

Work in progress. Design decisions: [docs/DECISIONS.md](docs/DECISIONS.md).

## Setup

```bash
uv sync
cp .env.example .env   # fill in keys
uv run pytest -q
```
