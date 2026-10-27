"""Three chunking strategies.

A. paragraph:       each blank-line-separated paragraph is one chunk
                    (a HotpotQA document is exactly one paragraph).
B. sentence_window: overlapping windows of `window` sentences, moving by `stride`.
                    Keeps sentence indices, so evaluation can check whether the
                    exact supporting sentence was retrieved.
C. recursive:       LangChain's RecursiveCharacterTextSplitter, fixed size with
                    overlap; used for uploaded long documents. Split per section,
                    so each chunk keeps its PDF page number.
"""

import re
import uuid

from langchain_text_splitters import RecursiveCharacterTextSplitter

from investigator.config import ChunkingConfig
from investigator.ingestion.documents import Chunk, Document

# Fixed namespace so chunk IDs are the same in every run (required by Qdrant: UUID or int).
CHUNK_NAMESPACE = uuid.UUID("6f1c2e1a-8d3b-4c55-9a77-2b0e5f3d9c41")

# Split after . ! ? when followed by whitespace and an upper-case letter, digit or quote.
# An approximation: it will also split after abbreviations like "Dr." before a name.
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"“(])")


def chunk_id_for(doc_id: str, index: int) -> str:
    return str(uuid.uuid5(CHUNK_NAMESPACE, f"{doc_id}:{index}"))


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_END.split(text) if s.strip()]


def window_starts(n_sentences: int, window: int, stride: int) -> list[int]:
    """Start positions of windows that together cover every sentence."""
    if n_sentences <= window:
        return [0]
    starts = list(range(0, n_sentences - window + 1, stride))
    if starts[-1] + window < n_sentences:  # stride skipped the tail: add a final window
        starts.append(n_sentences - window)
    return starts


def paragraph_chunks(doc: Document) -> list[Chunk]:
    pieces = [
        (para.strip(), section.page)
        for section in doc.sections
        for para in re.split(r"\n\s*\n", section.text)
        if para.strip()
    ]
    return [
        Chunk(chunk_id_for(doc.doc_id, i), doc.doc_id, i, doc.title, text, page=page)
        for i, (text, page) in enumerate(pieces)
    ]


def sentence_window_chunks(doc: Document, window: int, stride: int) -> list[Chunk]:
    # Page numbers are not tracked here: a window can cross a page boundary.
    sentences = doc.sentences if doc.sentences is not None else split_sentences(doc.text)
    chunks = []
    for i, start in enumerate(window_starts(len(sentences), window, stride)):
        end = min(start + window, len(sentences))
        text = " ".join(sentences[start:end])
        chunks.append(
            Chunk(
                chunk_id_for(doc.doc_id, i),
                doc.doc_id,
                i,
                doc.title,
                text,
                sent_start=start,
                sent_end=end,
            )
        )
    return chunks


def recursive_chunks(doc: Document, chunk_size: int, chunk_overlap: int) -> list[Chunk]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    pieces = [(text, s.page) for s in doc.sections for text in splitter.split_text(s.text)]
    return [
        Chunk(chunk_id_for(doc.doc_id, i), doc.doc_id, i, doc.title, text, page=page)
        for i, (text, page) in enumerate(pieces)
    ]


def chunk_document(doc: Document, strategy: str, cfg: ChunkingConfig) -> list[Chunk]:
    if strategy == "paragraph":
        return paragraph_chunks(doc)
    if strategy == "sentence_window":
        return sentence_window_chunks(doc, cfg.sentence_window.window, cfg.sentence_window.stride)
    if strategy == "recursive":
        return recursive_chunks(doc, cfg.recursive.chunk_size, cfg.recursive.chunk_overlap)
    raise ValueError(f"Unknown chunking strategy: {strategy}")
