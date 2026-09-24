from __future__ import annotations

import json
import queue
import threading
from pathlib import Path
from typing import Any

from .rag import RagService


def create_app(service: RagService):
    try:
        from fastapi import Body, FastAPI, HTTPException
        from fastapi.responses import FileResponse, StreamingResponse
        from fastapi.staticfiles import StaticFiles
    except ImportError as error:
        raise RuntimeError("FastAPI boundary requires the optional fastapi dependency") from error

    app = FastAPI(title="JJM RAG", version="1.0.0")
    static_root = Path(__file__).with_name("static")
    app.mount("/static", StaticFiles(directory=static_root), name="static")

    @app.get("/", include_in_schema=False)
    def chat_ui():
        # The console shell is tiny and references versioned static assets.
        # Avoid serving a stale shell after a frontend safety/clarification
        # update, which could otherwise hide controls returned by the API.
        return FileResponse(static_root / "index.html", headers={"Cache-Control": "no-store"})

    @app.get("/health")
    def health():
        return {"status": "healthy"}

    @app.get("/ready")
    def ready():
        return {"status": "degraded" if service.semantic is None or service.llm is None else "ready", "semantic_configured": service.semantic is not None, "llm_configured": service.llm is not None}

    def parse_request(request: dict[str, Any]) -> tuple[str, dict[str, Any], dict[str, Any], list[str]]:
        query_text = request.get("query")
        if not isinstance(query_text, str) or not query_text.strip() or len(query_text) > 8000:
            raise HTTPException(status_code=422, detail="query must be a non-empty string of at most 8000 characters")
        filters = request.get("filters", {})
        options = request.get("options", {})
        context = request.get("context", [])
        if not isinstance(filters, dict) or not isinstance(options, dict) or not isinstance(context, list) or not all(isinstance(item, str) and len(item) <= 1000 for item in context) or len(context) > 8:
            raise HTTPException(status_code=422, detail="filters and options must be objects; context must be at most eight short strings")
        return query_text, filters, options, context

    @app.post("/api/v1/query")
    def query(request: dict[str, Any] = Body(...)):
        try:
            query_text, filters, options, context = parse_request(request)
            response = service.query(query_text, filters=filters, retrieval_only=bool(options.get("retrieval_only")), context=context)
            return response.__dict__
        except Exception as error:
            raise HTTPException(status_code=503, detail="RAG provider unavailable") from error

    @app.post("/api/v1/query/stream")
    def query_stream(request: dict[str, Any] = Body(...)):
        query_text, filters, options, context = parse_request(request)

        def sse(event: str, payload: dict[str, Any]) -> str:
            return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

        def event_stream():
            events: queue.Queue[tuple[str, Any]] = queue.Queue()
            complete = threading.Event()

            def on_token(token: str) -> None:
                events.put(("token", token))

            def execute() -> None:
                try:
                    response = service.query(
                        query_text,
                        filters=filters,
                        retrieval_only=bool(options.get("retrieval_only")),
                        context=context,
                        on_token=on_token,
                    )
                    events.put(("final", response.__dict__))
                except Exception:
                    events.put(("error", {"detail": "RAG provider unavailable"}))
                finally:
                    complete.set()

            threading.Thread(target=execute, name="jjm-rag-stream", daemon=True).start()
            yield sse("status", {"stage": "retrieving"})
            while not complete.is_set() or not events.empty():
                try:
                    event, payload = events.get(timeout=0.25)
                except queue.Empty:
                    continue
                if event == "token":
                    yield sse("token", {"text": payload})
                else:
                    yield sse(event, payload)

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
        )

    return app
