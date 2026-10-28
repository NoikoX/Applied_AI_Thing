"""Gradio UI. Mounted inside the FastAPI app and calls the same service layer as the API."""

from pathlib import Path

import gradio as gr

from investigator.api.health import qdrant_is_reachable, rss_mb
from investigator.api.limits import client_key
from investigator.api.services import ServiceError, Services
from investigator.rag.schemas import RAGAnswer

STATUS_LABELS = {
    "answered": "✅ Answered",
    "contradictory": "⚠️ Sources disagree",
    "insufficient_evidence": "🚫 Not enough evidence in the documents",
    "unavailable": "⏳ Temporarily unavailable",
}
EXAMPLES = [
    "Which Emmett's Mark actor also played in the HBO series The Wire?",
    "Chikku Bhukku is based on a 2003 movie, which was directed by whom?",
    "Who was born first, Daphne du Maurier or Pietro di Donato?",
    "Who won the 2030 FIFA World Cup?",
]
DOC_COLUMNS = ["doc_id", "title", "format", "source", "n_chunks", "updated_at"]


def format_answer(a: RAGAnswer) -> tuple[str, str]:
    """(answer markdown, sources markdown)."""
    lines = [f"### {STATUS_LABELS.get(a.status, a.status)}", "", a.answer]
    if a.claims:
        lines += ["", "**Claims and their sources:**"]
        lines += [f"- {c['text']} " + " ".join(f"[{s}]" for s in c["sources"]) for c in a.claims]
    if a.refusal_reason:
        lines += ["", f"*Why:* {a.refusal_reason}"]
    for warning in a.warnings:
        lines += ["", f"> ⚠️ {warning}"]
    usage = a.usage or {}
    if usage.get("hops"):
        lines += ["", f"*Searched in {usage['hops']} round(s): {usage.get('queries')}*"]

    cited = {c.label for c in a.citations}
    sources = []
    for s in a.retrieved:
        marker = "**cited**" if s.label in cited else "retrieved"
        page = f", page {s.page}" if s.page else ""
        sources.append(f"**[{s.label}] {s.title}** ({marker}{page}, `{s.doc_id}`)\n\n{s.text}\n")
    return "\n".join(lines), "\n---\n".join(sources) or "*No sources retrieved.*"


def build_ui(services: Services) -> gr.Blocks:
    def ask(question: str, mode: str, request: gr.Request):
        client = client_key(dict(request.headers), request.client.host if request.client else None)
        try:
            a = services.ask(question, mode, client)
        except ServiceError as err:
            return f"### ❌ {err}", ""
        return format_answer(a)

    def upload(path: str | None, request: gr.Request):
        if not path:
            return "Choose a file first.", list_docs()
        client = client_key(dict(request.headers), request.client.host if request.client else None)
        try:
            r = services.upload(Path(path).name, Path(path).read_bytes(), client)
        except ServiceError as err:
            return f"❌ {err}", list_docs()
        note = f", duplicate of `{r.duplicate_of}`" if r.duplicate_of else ""
        return (
            f"`{r.doc_id}`: **{r.status}**, {r.n_chunks} chunk(s), "
            f"{r.n_near_duplicates} near-duplicate(s), {r.n_possible_conflicts} possible "
            f"conflict(s){note}",
            list_docs(),
        )

    def delete(doc_id: str, token: str):
        try:
            services.delete(doc_id.strip(), token or None)
        except ServiceError as err:
            return f"❌ {err}", list_docs()
        return f"Deleted `{doc_id}`.", list_docs()

    def list_docs():
        docs, _ = services.list_documents(limit=50)
        return [[d.get(c, "") for c in DOC_COLUMNS] for d in docs]

    def status() -> str:
        qdrant = "ok" if qdrant_is_reachable(services.qdrant) else "unreachable"
        lines = [f"- Qdrant: **{qdrant}**", f"- Memory: **{rss_mb():.0f} MB**"]
        gateway = services.extra_status.get("gateway")
        if gateway is not None:
            u = gateway.usage
            lines.append(
                f"- LLM calls since start: **{u.calls}** ({u.cached_calls} from cache), "
                f"cost **${u.cost_usd:.4f}**"
            )
        limits = services.settings.limits
        lines.append(
            f"- Limits: {limits.ask_per_minute_per_client}/min and "
            f"{limits.ask_per_day_per_client}/day per visitor, "
            f"{limits.ask_per_day_total}/day in total"
        )
        return "\n".join(lines)

    with gr.Blocks(title="AI Investigation Engine") as ui:
        gr.Markdown(
            "# AI Investigation Engine\n"
            "Ask questions that need facts from several documents. Answers cite their "
            "sources; the system says so when the documents disagree or do not contain "
            "the answer. Corpus: 46k Wikipedia paragraphs from HotpotQA."
        )
        with gr.Tab("Ask"):
            question = gr.Textbox(label="Question", lines=2, max_length=500)
            mode = gr.Radio(
                ["agent", "baseline"],
                value=services.settings.default_mode,
                label="Mode",
                info="agent: plans, searches in rounds, checks "
                "claims (slower). baseline: one search, one answer.",
            )
            ask_button = gr.Button("Ask", variant="primary")
            gr.Examples(EXAMPLES, inputs=question)
            answer_md = gr.Markdown()
            with gr.Accordion("Sources", open=True):
                sources_md = gr.Markdown()
            ask_button.click(ask, [question, mode], [answer_md, sources_md])
            question.submit(ask, [question, mode], [answer_md, sources_md])

        with gr.Tab("Documents"):
            gr.Markdown(
                "Upload PDF, DOCX, HTML, Markdown or text (max "
                f"{services.settings.max_upload_mb:g} MB). Uploading a file with the "
                "same name again updates it."
            )
            file = gr.File(
                label="File",
                type="filepath",
                file_types=[".pdf", ".docx", ".html", ".htm", ".md", ".txt"],
            )
            upload_button = gr.Button("Upload")
            upload_msg = gr.Markdown()
            table = gr.Dataframe(
                headers=DOC_COLUMNS, label="Documents (first 50)", interactive=False
            )
            gr.Button("Refresh list").click(list_docs, outputs=table)
            with gr.Row():
                doc_id = gr.Textbox(label="Document ID to delete")
                token = gr.Textbox(label="Admin token (only for corpus documents)", type="password")
            delete_button = gr.Button("Delete", variant="stop")
            delete_msg = gr.Markdown()
            upload_button.click(upload, file, [upload_msg, table])
            delete_button.click(delete, [doc_id, token], [delete_msg, table])

        with gr.Tab("Status"):
            status_md = gr.Markdown()
            gr.Button("Refresh").click(status, outputs=status_md)
    return ui
