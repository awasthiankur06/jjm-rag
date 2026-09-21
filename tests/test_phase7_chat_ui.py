from fastapi.testclient import TestClient

from jjm_rag.production.api import create_app
from jjm_rag.production.rag import QueryResponse


class FakeService:
    semantic = object()
    llm = object()

    def query(self, query, *, filters=None, retrieval_only=False, context=None):
        return QueryResponse(
            "request-1",
            "Grounded answer [1].",
            {"grounded": True, "level": "high", "evidence_count": 1},
            [{"content_unit_id": "content-1", "filename": "guide.pdf", "provenance_id": "prov-1", "source_type": "semantic"}],
            [],
            {"route": "semantic", "channels": ["semantic"], "candidate_count": 1},
            [],
        )


def test_chat_assets_use_existing_api_boundary():
    client = TestClient(create_app(FakeService()))
    assert client.get("/").status_code == 200
    assert "JJM RAG Console" in client.get("/").text
    assert client.get("/static/styles.css").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/health").json() == {"status": "healthy"}
    assert client.get("/ready").json()["status"] == "ready"
    response = client.post("/api/v1/query", json={"query": "test"})
    assert response.status_code == 200
    assert response.json()["citations"][0]["filename"] == "guide.pdf"
