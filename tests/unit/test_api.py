import pytest
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient

from investigator.api.main import create_app


class UnreachableQdrant:
    def get_collections(self):
        raise ConnectionError("cluster paused")


def make_client(qdrant) -> TestClient:
    # Models are not used by any M1 endpoint, so a placeholder avoids downloading them.
    return TestClient(create_app(qdrant, models=object()))


@pytest.fixture
def client():
    return make_client(QdrantClient(":memory:"))


def test_health_reports_memory(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["rss_mb"] > 0
    assert body["peak_rss_mb"] >= body["rss_mb"]


def test_deep_health_ok_when_qdrant_reachable(client):
    resp = client.get("/health/deep")
    assert resp.status_code == 200
    assert resp.json()["qdrant"] == "ok"


def test_deep_health_503_when_qdrant_down():
    resp = make_client(UnreachableQdrant()).get("/health/deep")
    assert resp.status_code == 503
    assert resp.json()["qdrant"] == "unreachable"


def test_root_redirects_to_ui(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert resp.headers["location"] == "/ui"


def test_ui_is_served(client):
    resp = client.get("/ui/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
