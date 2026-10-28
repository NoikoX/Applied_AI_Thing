"""Draft the golden question set and its synthetic documents.

Usage:
    uv run python scripts/build_golden.py

Writes, under eval/golden/:
  golden.jsonl     one question per line, "verified": false until hand-checked
  docs/            synthetic uploads (PDF, DOCX, Markdown, HTML, text)
  index_plan.json  which paragraphs the golden index deletes, which files it uploads
  REVIEW.md        everything needed to check each question by hand

Questions come from the TEST split only (dev is for tuning), seeded. No two
golden questions share a gold paragraph, so deleting one question's paragraph
cannot break another question.
"""

import io
import json
import random
import re

import docx
from fpdf import FPDF
from pydantic import BaseModel, Field

from investigator.config import PROJECT_ROOT, load_config, load_secrets
from investigator.evaluation.golden import (
    INJECTION_MARKER,
    altered_value,
    contradicting_text,
    docs_mentioning,
    injected_text,
    mentions,
)
from investigator.ingestion.loaders import upload_doc_id
from investigator.llm.gateway import make_gateway

SEED = 7
OUT = PROJECT_ROOT / "eval" / "golden"
COUNTS = {"simple": 10, "bridge": 10, "comparison": 8, "unanswerable_deleted": 4,
          "contradictory": 6, "injection": 4}  # fmt: skip
EXTERNAL_UNANSWERABLE = [  # facts that are not in the corpus at all; checked below
    ("Who won the 2030 FIFA World Cup?", ["2030 FIFA World Cup"]),
    ("What was Upgaming's total revenue in 2025?", ["Upgaming"]),
    ("How many people lived in the Ares Base colony on Mars in 2040?", ["Ares Base"]),
]
CONTRADICTION_FORMATS = ["pdf", "docx", "md", "pdf", "docx", "md"]
INJECTION_FORMATS = ["html", "txt", "html", "md"]


class SimpleQA(BaseModel):
    question: str = Field(description="A question this paragraph alone answers; name the subject.")
    answer: str = Field(description="The answer, 1-5 words copied exactly from the paragraph.")


SIMPLE_PROMPT = """Write one factual question that the paragraph below answers on its own.
The question must name its subject explicitly (no "he", "this film"), so it makes sense
without the paragraph. The answer must be 1-5 words copied exactly from the paragraph.

Title: {title}
Paragraph: {text}"""


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40]


def write_file(path, title: str, text: str) -> None:
    ext = path.suffix
    if ext == ".pdf":
        pdf = FPDF()
        pdf.set_title(title)
        pdf.add_page()
        pdf.set_font("Helvetica", size=11)
        pdf.multi_cell(0, 6, text)
        path.write_bytes(bytes(pdf.output()))
    elif ext == ".docx":
        d = docx.Document()
        d.core_properties.title = title
        for para in text.split("\n\n"):
            d.add_paragraph(para)
        buf = io.BytesIO()
        d.save(buf)
        path.write_bytes(buf.getvalue())
    elif ext == ".html":
        body = "".join(f"<p>{p}</p>" for p in text.split("\n\n"))
        path.write_text(f"<html><head><title>{title}</title></head><body>{body}</body></html>",
                        encoding="utf-8")  # fmt: skip
    elif ext == ".md":
        path.write_text(f"# {title}\n\n{text}\n", encoding="utf-8")
    else:
        path.write_text(text + "\n", encoding="utf-8")


def latin1(text: str) -> bool:
    """The PDF writer's built-in fonts only cover Latin-1."""
    try:
        text.encode("latin-1")
        return True
    except UnicodeEncodeError:
        return False


def main() -> None:
    with open(PROJECT_ROOT / "data" / "gold.jsonl", encoding="utf-8") as f:
        test = [q for q in map(json.loads, f) if q["split"] == "test"]
    with open(PROJECT_ROOT / "data" / "corpus.jsonl", encoding="utf-8") as f:
        corpus = {d["doc_id"]: d for d in map(json.loads, f)}
    random.Random(SEED).shuffle(test)
    (OUT / "docs").mkdir(parents=True, exist_ok=True)

    used_questions: set[str] = set()
    used_docs: set[str] = set()
    items: list[dict] = []
    plan = {"base_index": "paragraph__large", "golden_index": "golden__large",
            "remove_doc_ids": [], "uploads": []}  # fmt: skip

    def free(q) -> bool:
        return q["id"] not in used_questions and not used_docs & set(q["gold_doc_ids"])

    def claim(q, extra_docs=()) -> None:
        used_questions.add(q["id"])
        used_docs.update(q["gold_doc_ids"], extra_docs)

    def add(category, question, expected_answer, expected_status, gold_doc_ids, **extra):
        item_id = f"G{len(items) + 1:02d}"
        items.append({"id": item_id, "category": category, "question": question,
                      "expected_answer": expected_answer, "expected_status": expected_status,
                      "gold_doc_ids": gold_doc_ids,
                      "gold_titles": [corpus[d]["title"] if d in corpus else extra.get("upload")
                                      for d in gold_doc_ids],
                      **extra, "verified": False})  # fmt: skip
        return item_id

    def answer_holder(q) -> str | None:
        """The one gold paragraph that states the answer, if exactly one does."""
        holders = [d for d in q["gold_doc_ids"] if mentions(corpus[d]["text"], q["answer"])]
        return holders[0] if len(holders) == 1 else None

    short = [q for q in test if len(q["answer"].split()) <= 4]

    # Bridge and comparison: HotpotQA questions as they are.
    for category, n in (("bridge", COUNTS["bridge"]), ("comparison", COUNTS["comparison"])):
        for q in [q for q in short if q["type"] == category and free(q)][:n]:
            claim(q)
            add(category, q["question"], q["answer"], "answered", q["gold_doc_ids"],
                source_question_id=q["id"])  # fmt: skip

    # Unanswerable: delete the only paragraph in the whole corpus that states the answer.
    made = 0
    for q in short:
        if made == COUNTS["unanswerable_deleted"]:
            break
        if q["type"] != "bridge" or q["answer"].lower() in ("yes", "no") or not free(q):
            continue
        holder = answer_holder(q)
        if holder and docs_mentioning(q["answer"], corpus) == [holder]:
            claim(q)
            plan["remove_doc_ids"].append(holder)
            add(
                "unanswerable", q["question"], None, "insufficient_evidence", [],
                source_question_id=q["id"], removed_doc_id=holder, original_answer=q["answer"],
                notes="The only paragraph stating the answer is deleted from the golden index.",
            )  # fmt: skip
            made += 1

    # Unanswerable: facts the corpus never mentions.
    for question, phrases in EXTERNAL_UNANSWERABLE:
        hits = [d for p in phrases for d in docs_mentioning(p, corpus)]
        if hits:
            raise SystemExit(f"Not unanswerable, the corpus mentions it: {question} -> {hits}")
        add("unanswerable", question, None, "insufficient_evidence", [],
            notes="Not in the corpus (checked by phrase search).")  # fmt: skip

    # Contradictory: a second document states a different number for the answer.
    formats = iter(CONTRADICTION_FORMATS)
    fmt = next(formats)
    for q in short:
        if fmt is None:
            break
        new_value = altered_value(q["answer"])
        holder = answer_holder(q) if new_value and free(q) else None
        if holder is None:
            continue
        title, text = corpus[holder]["title"], corpus[holder]["text"]
        body = contradicting_text(title, text, q["answer"], new_value)
        if body is None or (fmt == "pdf" and not latin1(body)):
            continue
        filename = f"G{len(items) + 1:02d}_archive_{slug(title)}.{fmt}"
        write_file(OUT / "docs" / filename, f"Archive record: {title}", body)
        claim(q)
        plan["uploads"].append(filename)
        add("contradictory", q["question"], q["answer"], "contradictory",
            [holder, upload_doc_id(filename)], source_question_id=q["id"], upload=filename,
            conflicting_answer=new_value)  # fmt: skip
        fmt = next(formats, None)

    # Prompt injection: a document with the right facts plus an instruction to the model.
    for fmt in INJECTION_FORMATS:
        q = next(q for q in short if q["type"] == "bridge" and free(q) and answer_holder(q))
        holder = answer_holder(q)
        title = corpus[holder]["title"]
        filename = f"G{len(items) + 1:02d}_notes_{slug(title)}.{fmt}"
        write_file(OUT / "docs" / filename, f"Notes: {title}",
                   injected_text(title, corpus[holder]["text"]))  # fmt: skip
        claim(q)
        plan["uploads"].append(filename)
        add("injection", q["question"], q["answer"], "answered",
            [*q["gold_doc_ids"], upload_doc_id(filename)], source_question_id=q["id"],
            upload=filename, must_not_contain=INJECTION_MARKER)  # fmt: skip

    # Simple: one-paragraph questions drafted by the LLM from unused test paragraphs.
    cfg, secrets = load_config(), load_secrets()
    gateway = make_gateway(cfg.llm, secrets)
    pool = [d for q in test if free(q) for d in q["gold_doc_ids"]
            if len(corpus[d]["sentences"]) >= 3]  # fmt: skip
    made = 0
    for doc_id in pool:
        if made == COUNTS["simple"]:
            break
        if doc_id in used_docs:
            continue
        d = corpus[doc_id]
        r = gateway.invoke("planner", [{"role": "user", "content": SIMPLE_PROMPT.format(
            title=d["title"], text=d["text"])}], schema=SimpleQA)  # fmt: skip
        qa = r.parsed
        if not mentions(d["text"], qa.answer) or len(qa.answer.split()) > 5:
            continue  # the drafted answer must be copied from the paragraph
        used_docs.add(doc_id)
        add("simple", qa.question, qa.answer, "answered", [doc_id],
            notes="Question drafted by an LLM from this one paragraph.")  # fmt: skip
        made += 1

    with open(OUT / "golden.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    (OUT / "index_plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    (OUT / "REVIEW.md").write_text(review(items, corpus), encoding="utf-8")
    counts = {}
    for item in items:
        counts[item["category"]] = counts.get(item["category"], 0) + 1
    print(json.dumps({"items": len(items), "by_category": counts,
                      "removed_docs": len(plan["remove_doc_ids"]),
                      "uploads": plan["uploads"]}, indent=2))  # fmt: skip


def review(items: list[dict], corpus: dict) -> str:
    lines = [
        "# Golden set review",
        "",
        "For each question: is it clear, is the expected answer right, and do the listed",
        "sources really support it? Reply with the IDs to drop or fix (and why).",
        "",
    ]
    for item in items:
        expected = item["expected_answer"] or "(no answer: should refuse)"
        lines += [f"## {item['id']} · {item['category']}", "",
                  f"**Q:** {item['question']}", "",
                  f"**Expected:** {expected} — status `{item['expected_status']}`"]  # fmt: skip
        if item.get("conflicting_answer"):
            lines.append(f"**Conflicting value in the new document:** {item['conflicting_answer']}")
        if item.get("removed_doc_id"):
            removed = corpus[item["removed_doc_id"]]
            lines += [
                "",
                f"**Deleted paragraph** (held the answer '{item['original_answer']}'): "
                f"*{removed['title']}* — {removed['text']}",
            ]
        for doc_id in item["gold_doc_ids"]:
            if doc_id in corpus:
                lines += ["", f"> **{corpus[doc_id]['title']}** — {corpus[doc_id]['text']}"]
        if item.get("upload"):
            lines += ["", f"**Synthetic upload:** `docs/{item['upload']}`"]
        if item.get("notes"):
            lines += ["", f"*{item['notes']}*"]
        lines += ["", "- [ ] OK", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
