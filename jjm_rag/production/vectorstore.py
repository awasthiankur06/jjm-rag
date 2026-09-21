from __future__ import annotations

from typing import Any, Sequence

from jjm_rag.retrieval.interfaces import Evidence
from jjm_rag.semantic.contracts import SemanticDocument

from .providers import ProviderConfig, _post_json


class CloudVectorStore:
    """Generic managed vector HTTP adapter; provider-specific APIs stay behind this boundary."""

    def __init__(self, config: ProviderConfig | None = None, index: str | None = None, namespace: str | None = None):
        import os
        self.config = config or ProviderConfig.from_env("VECTOR", "")
        self.index = index or os.getenv("VECTOR_INDEX", "")
        self.namespace = namespace or os.getenv("VECTOR_NAMESPACE", "jjm")

    def upsert(self, records: Sequence[SemanticDocument], vectors: Sequence[Sequence[float]]) -> int:
        if not self.index:
            raise RuntimeError("VECTOR_INDEX is not configured")
        payload = {"index": self.index, "namespace": self.namespace, "vectors": [{"id": record.content_id, "values": list(vector), "metadata": {"document_id": record.document_id, "version_id": record.version_id, "filename": record.source_filename, "family": record.source_family, "report_type": record.report_type, "geography": record.geography, "reporting": record.reporting, "provenance": record.provenance, "content_hash": record.content_hash}} for record, vector in zip(records, vectors)]}
        _post_json(self.config, "/vectors/upsert", payload)
        return len(records)

    def query(self, vector: Sequence[float], *, top_k: int = 10, filters: dict[str, Any] | None = None) -> list[Evidence]:
        if not self.index:
            raise RuntimeError("VECTOR_INDEX is not configured")
        response = _post_json(self.config, "/query", {"index": self.index, "namespace": self.namespace, "vector": list(vector), "top_k": top_k, "filter": filters or {}})
        results = []
        for match in response.get("matches", []):
            metadata = match.get("metadata", {})
            if metadata.get("filename") == "Status of Pipe Water Supply in School (2).xls":
                continue
            results.append(Evidence(str(match.get("id")), metadata.get("filename", ""), {"content_unit_id": match.get("id")}, "semantic", float(match.get("score", 0.0)), metadata.get("text", ""), metadata))
        return results


class CloudSemanticRetriever:
    def __init__(self, embeddings, vector_store: CloudVectorStore):
        self.embeddings = embeddings
        self.vector_store = vector_store

    def search(self, query: str, filters: dict[str, str], limit: int) -> list[Evidence]:
        return self.vector_store.query(self.embeddings.embed_query(query), top_k=limit, filters=filters)
