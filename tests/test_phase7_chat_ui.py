from fastapi.testclient import TestClient

from jjm_rag.production.api import create_app
from jjm_rag.production.rag import QueryResponse


class FakeService:
    semantic = object()
    llm = object()

    def query(self, query, *, filters=None, retrieval_only=False, context=None, on_token=None):
        if on_token is not None:
            on_token("Grounded ")
            on_token("answer [1].")
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
    app_js = client.get("/static/app.js")
    assert app_js.status_code == 200
    assert "citation-link" not in app_js.text
    assert "async function askQuestion(question, isClarificationChoice = false)" in app_js.text
    assert "isClarificationChoice && pendingClarification?.originalQuestion" in app_js.text
    assert client.get("/health").json() == {"status": "healthy"}
    assert client.get("/ready").json()["status"] == "ready"
    response = client.post("/api/v1/query", json={"query": "test"})
    assert response.status_code == 200
    assert response.json()["citations"][0]["filename"] == "guide.pdf"
    streamed = client.post("/api/v1/query/stream", json={"query": "test"})
    assert streamed.status_code == 200
    assert streamed.headers["content-type"].startswith("text/event-stream")
    assert 'event: token\ndata: {"text": "Grounded "}' in streamed.text
    assert "event: final" in streamed.text
    assert "/api/v1/query/stream" in app_js.text
    assert "consumeSse" in app_js.text
