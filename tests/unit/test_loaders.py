import io

import docx
import pytest
from fpdf import FPDF

from investigator.ingestion.loaders import (
    EmptyDocumentError,
    UnsupportedFormatError,
    load_bytes,
    load_corpus_record,
    upload_doc_id,
)


def make_pdf(pages: list[str], title: str = "Incident Report") -> bytes:
    pdf = FPDF()
    pdf.set_title(title)
    pdf.set_author("Ops Team")
    pdf.set_font("Helvetica", size=12)
    for text in pages:
        pdf.add_page()
        pdf.multi_cell(0, 10, text)
    return bytes(pdf.output())


def make_docx(paragraphs: list[str], title: str = "") -> bytes:
    d = docx.Document()
    d.core_properties.title = title
    d.core_properties.author = "Noe"
    for p in paragraphs:
        d.add_paragraph(p)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def test_pdf_keeps_pages_and_metadata():
    doc = load_bytes("report.pdf", make_pdf(["Payment delay in March.", "Service B affected."]))
    assert doc.format == "pdf"
    assert doc.title == "Incident Report"
    assert [s.page for s in doc.sections] == [1, 2]
    assert "Service B affected." in doc.sections[1].text
    assert doc.metadata["n_pages"] == 2
    assert doc.metadata["author"] == "Ops Team"
    assert "created" in doc.metadata


def test_pdf_without_text_is_rejected():
    with pytest.raises(EmptyDocumentError, match="OCR"):
        load_bytes("scan.pdf", make_pdf([""]))


def test_docx_text_and_metadata():
    doc = load_bytes("notes.docx", make_docx(["First point.", "Second point."], title="Notes"))
    assert doc.format == "docx"
    assert doc.title == "Notes"
    assert doc.text == "First point.\n\nSecond point."
    assert doc.metadata["author"] == "Noe"


def test_docx_without_title_falls_back_to_file_name():
    assert load_bytes("Q1 summary.docx", make_docx(["x"])).title == "Q1 summary"


def test_html_drops_scripts_and_uses_title_tag():
    html = b"""<html><head><title>Change Log</title><style>p{}</style></head>
    <body><script>alert(1)</script><h1>March</h1><p>Deployed v2.</p></body></html>"""
    doc = load_bytes("log.html", html)
    assert doc.title == "Change Log"
    assert "alert" not in doc.text and "p{}" not in doc.text
    assert "March" in doc.text and "Deployed v2." in doc.text


def test_markdown_heading_becomes_title():
    doc = load_bytes("runbook.md", b"# Payment Runbook\n\nRestart the queue.\n")
    assert doc.format == "md"
    assert doc.title == "Payment Runbook"


def test_text_title_from_file_name_and_blank_lines_collapsed():
    doc = load_bytes("notes.txt", b"a\n\n\n\n b \n")
    assert doc.title == "notes"
    assert doc.text == "a\n\nb"


def test_unsupported_extension_rejected():
    with pytest.raises(UnsupportedFormatError, match=".exe"):
        load_bytes("tool.exe", b"MZ")


def test_empty_text_file_rejected():
    with pytest.raises(EmptyDocumentError):
        load_bytes("empty.txt", b"  \n\n ")


def test_same_file_name_gives_same_doc_id():
    assert upload_doc_id("Report.PDF") == upload_doc_id("report.pdf")
    assert upload_doc_id("a.pdf") != upload_doc_id("b.pdf")
    assert load_bytes("a.txt", b"one").doc_id == load_bytes("a.txt", b"two").doc_id


def test_corpus_record_keeps_sentences():
    rec = {
        "doc_id": "hp_1",
        "title": "Paris",
        "text": "A. B.",
        "sentences": ["A.", "B."],
        "source": "hotpotqa",
        "question_ids": ["q1"],
    }
    doc = load_corpus_record(rec)
    assert doc.format == "hotpotqa"
    assert doc.sentences == ["A.", "B."]
    assert doc.text == "A. B."
