import pytest

from investigator.config import load_config
from investigator.ingestion.chunking import (
    chunk_document,
    paragraph_chunks,
    recursive_chunks,
    sentence_window_chunks,
    split_sentences,
    window_starts,
)
from investigator.ingestion.documents import Document, Section

CFG = load_config().chunking


def corpus_doc(sentences: list[str]) -> Document:
    return Document(
        doc_id="hp_test",
        title="T",
        source="hotpotqa",
        format="hotpotqa",
        sections=[Section(" ".join(sentences))],
        sentences=sentences,
    )


@pytest.mark.parametrize(
    "n, expected",
    [(1, [0]), (3, [0]), (4, [0, 1]), (5, [0, 2]), (6, [0, 2, 3]), (7, [0, 2, 4])],
)
def test_window_starts(n, expected):
    assert window_starts(n, window=3, stride=2) == expected


@pytest.mark.parametrize("n", range(1, 30))
def test_windows_cover_every_sentence(n):
    covered = {i for s in window_starts(n, 3, 2) for i in range(s, min(s + 3, n))}
    assert covered == set(range(n))


def test_sentence_windows_keep_sentence_ranges():
    sentences = [f"Sentence {i}." for i in range(5)]
    chunks = sentence_window_chunks(corpus_doc(sentences), window=3, stride=2)
    assert [(c.sent_start, c.sent_end) for c in chunks] == [(0, 3), (2, 5)]
    assert chunks[1].text == "Sentence 2. Sentence 3. Sentence 4."


def test_sentence_windows_split_text_when_no_sentences_given():
    doc = Document("up_x", "T", "x.txt", "txt", [Section("One here. Two here! Three? Four.")])
    chunks = sentence_window_chunks(doc, window=3, stride=2)
    assert [c.text for c in chunks] == ["One here. Two here! Three?", "Two here! Three? Four."]


def test_split_sentences():
    assert split_sentences("He left. She stayed! Why? 3 days.") == [
        "He left.",
        "She stayed!",
        "Why?",
        "3 days.",
    ]


def test_hotpotqa_doc_is_one_paragraph_chunk():
    chunks = paragraph_chunks(corpus_doc(["A b.", "C d."]))
    assert len(chunks) == 1
    assert chunks[0].text == "A b. C d."


def test_paragraph_chunks_split_on_blank_lines_and_keep_page():
    doc = Document(
        "up_x", "T", "x.pdf", "pdf", [Section("p1\n\np2", page=1), Section("p3", page=2)]
    )
    chunks = paragraph_chunks(doc)
    assert [(c.text, c.page) for c in chunks] == [("p1", 1), ("p2", 1), ("p3", 2)]
    assert [c.index for c in chunks] == [0, 1, 2]


def test_recursive_chunks_respect_size_overlap_and_pages():
    words = " ".join(f"word{i}" for i in range(300))  # about 2,400 characters
    doc = Document("up_x", "T", "x.pdf", "pdf", [Section(words, page=1), Section("end", page=2)])
    chunks = recursive_chunks(doc, chunk_size=500, chunk_overlap=100)
    assert all(len(c.text) <= 500 for c in chunks)
    assert chunks[-1].page == 2 and chunks[0].page == 1
    first_words, second_words = chunks[0].text.split(), chunks[1].text.split()
    assert first_words[-1] in second_words  # overlap carries text into the next chunk


def test_chunk_ids_are_deterministic_and_unique():
    doc = corpus_doc([f"S{i}." for i in range(9)])
    a = [c.chunk_id for c in sentence_window_chunks(doc, 3, 2)]
    b = [c.chunk_id for c in sentence_window_chunks(doc, 3, 2)]
    assert a == b
    assert len(set(a)) == len(a)


def test_chunk_document_dispatches_and_rejects_unknown_strategy():
    doc = corpus_doc(["A.", "B.", "C.", "D."])
    assert len(chunk_document(doc, "sentence_window", CFG)) == 2
    with pytest.raises(ValueError, match="Unknown"):
        chunk_document(doc, "magic", CFG)
