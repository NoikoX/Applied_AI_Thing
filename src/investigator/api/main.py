"""FastAPI application with the Gradio UI mounted at /ui.

Production entry point:
    uvicorn investigator.api.main:build_app --factory
"""

import gradio as gr
from fastapi import FastAPI, Response
from fastapi.responses import RedirectResponse
from qdrant_client import QdrantClient

from investigator.api.health import peak_rss_mb, qdrant_is_reachable, rss_mb
from investigator.config import load_config, load_secrets
from investigator.index.qdrant_store import connect
from investigator.retrieval.local_models import LocalModels, load_local_models, warm_up
from investigator.ui.gradio_app import build_ui


def create_app(qdrant: QdrantClient, models: LocalModels) -> FastAPI:
    """Build the app from already-created dependencies (tests pass fakes)."""
    app = FastAPI(title="AI Investigation Engine")
    app.state.qdrant = qdrant
    app.state.models = models

    @app.get("/health")
    def health() -> dict:
        """Liveness: cheap, no external calls. Used by Render's health check."""
        return {
            "status": "ok",
            "rss_mb": round(rss_mb(), 1),
            "peak_rss_mb": round(peak_rss_mb(), 1),
        }

    @app.get("/health/deep")
    def health_deep(response: Response) -> dict:
        """Readiness: runs a real Qdrant call. Used by the daily keep-alive job."""
        ok = qdrant_is_reachable(qdrant)
        if not ok:
            response.status_code = 503
        return {"status": "ok" if ok else "degraded", "qdrant": "ok" if ok else "unreachable"}

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse("/ui")

    def status_text() -> str:
        qdrant_state = "ok" if qdrant_is_reachable(qdrant) else "unreachable"
        return f"Qdrant: **{qdrant_state}** · Memory: **{rss_mb():.0f} MB**"

    # ssr_mode=False: server-side rendering would start a Node.js process and cost memory.
    return gr.mount_gradio_app(app, build_ui(status_text), path="/ui", ssr_mode=False)


def build_app() -> FastAPI:
    cfg = load_config()
    secrets = load_secrets()
    models = load_local_models(cfg.local_models)
    warm_up(models)
    return create_app(connect(secrets), models)
