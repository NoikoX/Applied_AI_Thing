"""Document and chunk data structures shared by loading, chunking and indexing."""

from dataclasses import dataclass, field

from investigator.ingestion.dedup import content_hash


@dataclass
class Section:
    """A piece of a document with its own location, e.g. one PDF page."""

    text: str
    page: int | None = None  # 1-based, PDF only


@dataclass
class Document:
    doc_id: str
    title: str
    source: str  # "hotpotqa" or the uploaded file name
    format: str  # pdf, docx, html, md, txt, hotpotqa
    sections: list[Section]
    metadata: dict = field(default_factory=dict)
    sentences: list[str] | None = None  # given by the dataset; otherwise split on demand

    @property
    def text(self) -> str:
        return "\n\n".join(s.text for s in self.sections)

    @property
    def content_hash(self) -> str:
        return content_hash(self.title, self.text)


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    index: int
    title: str
    text: str
    page: int | None = None
    sent_start: int | None = None  # sentence range [start, end), sentence-window strategy only
    sent_end: int | None = None
