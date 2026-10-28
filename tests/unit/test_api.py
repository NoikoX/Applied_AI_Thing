import pytest
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient

from investigator.api.limits import RequestLimiter
from investigator.api.main import create_app
from investigator.api.services import Services
from investigator.config import load_config
from investigator.index.qdrant_store import ensure_collections
from investigator.index.registry import DocumentIndex
from investigator.ingestion.documents import Document, Section
from investigator.rag.schemas import Citation, RAGAnswer
from tests.fakes import FakeSparse, HashEmbedder

CFG = load_config()
TOKEN = "test-admin-token"
SOURCE = Citation("S1", "c1", "hp_1", "John Doman", "John Doman played Rawls in The Wire.")


class FixedQA:
    def __init__(self):
        self.questions = []

    def answer(self, question):
        self.questions.append(question)
        return RAGAnswer(
            question,
            "answered",
            "John Doman",
            claims=[{"text": "John Doman was in The Wire.", "sources": ["S1"]}],
            citations=[SOURCE],
            retrieved=[SOURCE],
            usage={"llm_calls": 5, "llm_call_log": [{"big": "x"}], "hops": 2},
        )


class UnreachableQdrant:
    def get_collections(self):
        raise ConnectionError("cluster paused")


def make_services(per_minute=100, per_day=100, total=1000, uploads=100, qdrant=None):
    client = QdrantClient(":memory:")
    embedder = HashEmbedder()
    ensure_collections(client, "paragraph", embedder.model, embedder.dimensions)
    index = DocumentIndex(client, "paragraph", CFG.chunking, embedder, FakeSparse(), 0.95)
    index.add_many(
        [
            Document(
                "hp_1",
                "John Doman",
                "hotpotqa",
                "hotpotqa",
                [Section("John Doman played Rawls.")],
                sentences=["x"],
            )
        ]
    )
    return Services(
        qdrant=qdrant or client,
        index=index,
        systems={"agent": FixedQA(), "baseline": FixedQA()},
        settings=CFG.app.model_copy(update={"max_upload_mb": 0.001}),  # about 1 KB
        admin_token=TOKEN,
        ask_limiter=RequestLimiter(per_minute, per_day, total),
        upload_limiter=RequestLimiter(uploads, uploads),
    )


@pytest.fixture
def services():
    return make_services()


@pytest.fixture
def client(services):
    return TestClient(create_app(services))


# ---- health -----------------------------------------------------------------


def test_health_reports_memory(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["peak_rss_mb"] >= body["rss_mb"] > 0


def test_deep_health_ok_and_503_when_qdrant_down(client):
    assert client.get("/health/deep").json()["qdrant"] == "ok"
    down = TestClient(create_app(make_services(qdrant=UnreachableQdrant())))
    resp = down.get("/health/deep")
    assert resp.status_code == 503 and resp.json()["qdrant"] == "unreachable"


def test_web_page_is_served_and_never_renders_server_text_as_html(client):
    resp = client.get("/")
    assert resp.status_code == 200 and "text/html" in resp.headers["content-type"]
    page = resp.text
    assert "/api/ask" in page and "/api/documents" in page and "/api/status" in page
    # Document text is untrusted (anyone can upload): the page must insert it as text only.
    script = page.split("<script>")[1]
    assert ".innerHTML" not in script and "insertAdjacentHTML" not in script


def test_status_endpoint(client):
    body = client.get("/api/status").json()
    assert body["qdrant"] == "ok" and body["memory_mb"] > 0
    assert body["limits"]["ask_per_day_total"] == CFG.app.limits.ask_per_day_total


# ---- ask ----------------------------------------------------------------------


def test_ask_returns_answer_with_sources_and_default_mode(client, services):
    body = client.post("/api/ask", json={"question": "Who played Rawls?"}).json()
    assert body["status"] == "answered" and body["answer"] == "John Doman"
    assert body["citations"][0]["title"] == "John Doman"
    assert "llm_call_log" not in body["usage"] and body["usage"]["hops"] == 2
    assert services.systems[CFG.app.default_mode].questions == ["Who played Rawls?"]


def test_ask_baseline_mode(client, services):
    client.post("/api/ask", json={"question": "Who played Rawls?", "mode": "baseline"})
    assert services.systems["baseline"].questions == ["Who played Rawls?"]


@pytest.mark.parametrize(
    "body",
    [{"question": "hi"}, {"question": "x" * 501}, {"question": "valid question", "mode": "magic"}],
)
def test_invalid_questions_are_rejected(client, body):
    assert client.post("/api/ask", json=body).status_code == 422


def test_rate_limit_returns_429(services):
    client = TestClient(create_app(make_services(per_minute=2)))
    for _ in range(2):
        assert client.post("/api/ask", json={"question": "Who played Rawls?"}).status_code == 200
    resp = client.post("/api/ask", json={"question": "Who played Rawls?"})
    assert resp.status_code == 429 and "try again" in resp.json()["detail"]


def test_rate_limit_is_per_client():
    client = TestClient(create_app(make_services(per_minute=1)))
    for ip in ("1.1.1.1", "2.2.2.2"):
        resp = client.post(
            "/api/ask", json={"question": "Who played Rawls?"}, headers={"X-Forwarded-For": ip}
        )
        assert resp.status_code == 200


# ---- documents --------------------------------------------------------------------


def upload(client, name="notes.txt", data=b"The outage began on 12 March."):
    return client.post("/api/documents", files={"file": (name, data)})


def test_upload_update_and_duplicate(client):
    first = upload(client).json()
    assert first["status"] == "added" and first["doc_id"].startswith("up_")
    assert upload(client).json()["status"] == "unchanged"
    assert upload(client, data=b"The outage began on 14 March.").json()["status"] == "updated"


@pytest.mark.parametrize(
    "name, data, code",
    [
        ("tool.exe", b"MZ", 400),
        ("empty.txt", b"   ", 400),
        ("big.txt", b"x" * 5000, 413),
    ],
)
def test_bad_uploads(client, name, data, code):
    resp = upload(client, name, data)
    assert resp.status_code == code and resp.json()["detail"]


def test_upload_limit():
    client = TestClient(create_app(make_services(uploads=1)))
    assert upload(client, "a.txt").status_code == 200
    assert upload(client, "b.txt").status_code == 429


def test_list_and_get_documents(client):
    upload(client)
    docs = client.get("/api/documents").json()["documents"]
    assert {d["doc_id"][:3] for d in docs} == {"hp_", "up_"}
    assert client.get("/api/documents/hp_1").json()["title"] == "John Doman"
    assert client.get("/api/documents/hp_missing").status_code == 404


def test_anyone_can_delete_uploads_but_corpus_needs_the_token(client):
    doc_id = upload(client).json()["doc_id"]
    assert client.delete(f"/api/documents/{doc_id}").status_code == 204
    assert client.delete("/api/documents/hp_1").status_code == 403
    assert (
        client.delete("/api/documents/hp_1", headers={"X-Admin-Token": "wrong"}).status_code == 403
    )
    assert client.delete("/api/documents/hp_1", headers={"X-Admin-Token": TOKEN}).status_code == 204
    assert client.delete("/api/documents/hp_1", headers={"X-Admin-Token": TOKEN}).status_code == 404


# ---- UI formatting ------------------------------------------------------------------


def test_production_services_skip_the_reranker_when_overridden():
    from investigator.config import with_overrides

    retrieval = with_overrides(CFG.retrieval, CFG.app.retrieval_overrides)
    assert retrieval.rerank is False and CFG.retrieval.rerank is True  # eval keeps it on
