"""FastAPI application: REST API under /api, Gradio UI mounted at /ui, health checks.

Production entry point:
    uvicorn investigator.api.main:build_app --factory
"""

import gradio as gr
from fastapi import FastAPI, File, Header, Request, Response, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse

from investigator.api.health import peak_rss_mb, qdrant_is_reachable, rss_mb
from investigator.api.limits import client_key
from investigator.api.schemas import AnswerOut, AskIn, DocumentPage, UploadOut
from investigator.api.services import ServiceError, Services, build_services
from investigator.config import load_config, load_secrets
from investigator.ui.gradio_app import build_ui


def create_app(services: Services) -> FastAPI:
    """Build the app from already-created services (tests pass fakes)."""
    app = FastAPI(
        title="AI Investigation Engine",
        description="Multi-hop question answering over documents, with citations.",
    )
    app.state.services = services

    @app.exception_handler(ServiceError)
    def service_error(request: Request, err: ServiceError) -> JSONResponse:
        return JSONResponse(status_code=err.status_code, content={"detail": str(err)})

    @app.get("/health")
    def health() -> dict:
        """Liveness: cheap, no external calls. Used by Render's health check."""
        current = rss_mb()
        return {
            "status": "ok",
            "rss_mb": round(current, 1),
            "peak_rss_mb": round(max(peak_rss_mb(), current), 1),
        }

    @app.get("/health/deep")
    def health_deep(response: Response) -> dict:
        """Readiness: runs a real Qdrant call. Used by the daily keep-alive job."""
        ok = qdrant_is_reachable(services.qdrant)
        if not ok:
            response.status_code = 503
        return {"status": "ok" if ok else "degraded", "qdrant": "ok" if ok else "unreachable"}

    @app.post("/api/ask", response_model=AnswerOut)
    def ask(body: AskIn, request: Request) -> AnswerOut:
        mode = body.mode or services.settings.default_mode
        client = client_key(dict(request.headers), request.client.host if request.client else None)
        return AnswerOut.from_answer(services.ask(body.question, mode, client))

    @app.get("/api/documents", response_model=DocumentPage)
    def list_documents(limit: int = 50, offset: str | None = None) -> DocumentPage:
        docs, next_offset = services.list_documents(limit, offset)
        return DocumentPage(documents=docs, next_offset=str(next_offset) if next_offset else None)

    @app.get("/api/documents/{doc_id}")
    def get_document(doc_id: str) -> dict:
        return services.get_document(doc_id)

    @app.post("/api/documents", response_model=UploadOut)
    async def upload(request: Request, file: UploadFile = File(...)) -> UploadOut:  # noqa: B008
        data = await file.read()
        client = client_key(dict(request.headers), request.client.host if request.client else None)
        r = services.upload(file.filename or "upload", data, client)
        return UploadOut(
            doc_id=r.doc_id,
            status=r.status,
            n_chunks=r.n_chunks,
            n_near_duplicates=r.n_near_duplicates,
            n_possible_conflicts=r.n_possible_conflicts,
            duplicate_of=r.duplicate_of,
        )

    @app.delete("/api/documents/{doc_id}", status_code=204)
    def delete(doc_id: str, x_admin_token: str | None = Header(default=None)) -> Response:
        services.delete(doc_id, x_admin_token)
        return Response(status_code=204)

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse("/ui")

    # ssr_mode=False: server-side rendering would start a Node.js process and cost memory.
    return gr.mount_gradio_app(app, build_ui(services), path="/ui", ssr_mode=False)


def build_app() -> FastAPI:
    return create_app(build_services(load_config(), load_secrets()))
