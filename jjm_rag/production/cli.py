from __future__ import annotations

import argparse
import json

from jjm_rag.config import settings as _settings
from jjm_rag.persistence.database import get_database_session

from .gemini import GeminiEmbeddingProvider
from .postgres_store import PostgresEvidenceStore
from .providers import ProviderError, XaiLLMProvider
from .qdrant import CanonicalValidatedQdrantRetriever, QdrantSemanticRetriever, QdrantCloudStore
from .rag import RagService


def build_service() -> RagService:
    connection = get_database_session()
    store = PostgresEvidenceStore(connection)
    semantic = None
    llm = None
    try:
        embeddings = GeminiEmbeddingProvider()
        vector_store = QdrantCloudStore()
        if embeddings.configured and vector_store.configured:
            semantic = CanonicalValidatedQdrantRetriever(
                QdrantSemanticRetriever(embeddings, vector_store), connection
            )
    except (ProviderError, RuntimeError):
        semantic = None
    try:
        candidate = XaiLLMProvider()
        if candidate.config.api_key:
            llm = candidate
    except ProviderError:
        llm = None
    return RagService(store, semantic=semantic, llm=llm, require_llm=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="JJM cloud-only RAG query")
    parser.add_argument("query")
    parser.add_argument("--retrieval-only", action="store_true")
    args = parser.parse_args()
    response = build_service().query(args.query, retrieval_only=args.retrieval_only)
    print(json.dumps(response.__dict__, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
