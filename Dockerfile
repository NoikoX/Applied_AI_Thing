FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.8.3 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    GRADIO_ANALYTICS_ENABLED=False \
    PATH="/app/.venv/bin:$PATH"

# Dependencies first, so code changes don't reinstall them.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project

COPY src ./src
COPY config ./config
RUN uv sync --locked --no-dev

# Download the ONNX models into the image: the free host's disk is wiped on
# every restart, so downloading at startup would repeat on every cold start.
RUN python -m investigator.retrieval.local_models

# Render sets PORT; 10000 is its default.
CMD ["sh", "-c", "uvicorn investigator.api.main:build_app --factory --host 0.0.0.0 --port ${PORT:-10000}"]
