"""Gradio UI. Mounted inside the FastAPI app, so both share one process."""

from collections.abc import Callable

import gradio as gr


def build_ui(status_text: Callable[[], str]) -> gr.Blocks:
    with gr.Blocks(title="AI Investigation Engine") as ui:
        gr.Markdown(
            "# AI Investigation Engine\n"
            "Work in progress: question answering arrives in a later milestone."
        )
        status = gr.Markdown()
        gr.Button("Check status").click(status_text, outputs=status)
    return ui
