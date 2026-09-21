from __future__ import annotations

import os
import uuid
from typing import Any, Sequence

from jjm_rag.retrieval.interfaces import Evidence
from jjm_rag.semantic.contracts import SemanticDocument

from .providers import ProviderError


class QdrantCloudStore:
    """Qdrant Cloud adapter with non-destructive collection validation."""

    def __init__(self, url: str | None = None, api_key: str | None = None, collection: str | None = None, client: Any | None = None):
        self.url = os.getenv("QDRANT_URL", "") if url is None else url
        self.api_key = api_key if api_key is not None else os.getenv("QDRANT_API_KEY", "")
        self.collection = os.getenv("QDRANT_COLLECTION", "") if collection is None else collection
        self.timeout = float(os.getenv("QDRANT_TIMEOUT", "60"))
        self._client = client

    @property
    def configured(self) -> bool:
        local = self.url.startswith("http://localhost") or self.url.startswith("http://127.0.0.1")
        return bool(self.url and self.collection and (self.api_key or local))

    @staticmethod
    def point_id(content_unit_id: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"jjm-rag:{content_unit_id}"))

    def _get_client(self):
        if self._client is None:
            if not self.configured:
                raise ProviderError("QDRANT_URL, QDRANT_API_KEY, and QDRANT_COLLECTION are required")
            try:
                from qdrant_client import QdrantClient
            except ImportError as error:
                raise ProviderError("qdrant-client package is not installed") from error
            self._client = QdrantClient(url=self.url, api_key=self.api_key or None, timeout=self.timeout, check_compatibility=False)
        return self._client

    def inspect_collection(self) -> dict[str, Any]:
        client = self._get_client()
        try:
            info = client.get_collection(self.collection)
        except Exception as error:
            if "not found" in str(error).lower() or "404" in str(error):
                return {"exists": False}
            raise ProviderError("Qdrant collection inspection failed") from error
        config = info.config.params.vectors
        size = getattr(config, "size", None)
        distance = getattr(getattr(config, "distance", None), "name", str(getattr(config, "distance", "")))
        return {"exists": True, "size": size, "distance": distance}

    def ensure_collection(self, dimension: int) -> dict[str, Any]:
        state = self.inspect_collection()
        if state["exists"]:
            if state.get("size") != dimension or str(state.get("distance", "")).upper() not in {"COSINE", "DISTANCE.COSINE"}:
                raise ProviderError("Qdrant collection has incompatible vector configuration")
            return state
        client = self._get_client()
        try:
            from qdrant_client.http import models
            client.create_collection(self.collection, vectors_config=models.VectorParams(size=dimension, distance=models.Distance.COSINE))
        except Exception as error:
            raise ProviderError("Qdrant collection creation failed") from error
        return {"exists": True, "size": dimension, "distance": "COSINE", "created": True}

    def ensure_payload_indexes(self) -> list[str]:
        client = self._get_client()
        fields = ["state", "district", "report_type", "financial_year", "reporting_date", "source_document_id", "source_version_id", "corpus_version"]
        try:
            from qdrant_client.http import models
            for field in fields:
                client.create_payload_index(self.collection, field_name=field, field_schema=models.PayloadSchemaType.KEYWORD, wait=True)
        except Exception as error:
            raise ProviderError("Qdrant payload index creation failed") from error
        return fields

    def upsert(self, records: Sequence[SemanticDocument], vectors: Sequence[Sequence[float]]) -> int:
        if len(records) != len(vectors):
            raise ProviderError("Qdrant records and vectors have different lengths")
        client = self._get_client()
        try:
            from qdrant_client.http import models
            points = [models.PointStruct(id=self.point_id(record.content_id), vector=list(vector), payload={"content_unit_id": record.content_id, "document_id": record.document_id, "version_id": record.version_id, "filename": record.source_filename, "family": record.source_family, "report_type": record.report_type, "geography": record.geography, "reporting": record.reporting, "provenance": record.provenance, "content_hash": record.content_hash, "text": record.text, "embedding_provider": record.embedding_provider, "embedding_model": record.model_name, "embedding_dimension": record.embedding_dimension}) for record, vector in zip(records, vectors)]
            client.upsert(self.collection, points=points, wait=True)
        except Exception as error:
            raise ProviderError("Qdrant upsert failed") from error
        return len(points)

    def count(self) -> int:
        client = self._get_client()
        try:
            return int(client.count(self.collection, exact=True).count)
        except Exception as error:
            raise ProviderError("Qdrant count failed") from error

    def search(self, vector: Sequence[float], *, limit: int = 10, filters: dict[str, Any] | None = None) -> list[Evidence]:
        client = self._get_client()
        try:
            from qdrant_client.http import models
            conditions = []
            for key, value in (filters or {}).items():
                conditions.append(models.FieldCondition(key=key, match=models.MatchValue(value=value)))
            query_filter = models.Filter(must=conditions) if conditions else None
            if hasattr(client, "query_points"):
                points = client.query_points(self.collection, query=list(vector), query_filter=query_filter, limit=limit, with_payload=True).points
            else:
                points = client.search(self.collection, query_vector=list(vector), query_filter=query_filter, limit=limit)
        except Exception as error:
            raise ProviderError("Qdrant search failed") from error
        results = []
        for point in points:
            payload = point.payload or {}
            if payload.get("filename") == "Status of Pipe Water Supply in School (2).xls":
                continue
            content_unit_id = payload.get("content_unit_id", str(point.id))
            results.append(Evidence(str(content_unit_id), payload.get("filename", ""), {"content_unit_id": content_unit_id}, "semantic", float(point.score), payload.get("text", ""), payload))
        return results


class QdrantSemanticRetriever:
    def __init__(self, embeddings, store: QdrantCloudStore):
        self.embeddings = embeddings
        self.store = store

    def search(self, query: str, filters: dict[str, str], limit: int) -> list[Evidence]:
        return self.store.search(self.embeddings.embed_query(query), limit=limit, filters=filters)


class CanonicalValidatedQdrantRetriever:
    """Permit only semantic points that still match canonical PostgreSQL text.

    Vector indexes are derived and can lag a canonical rebuild.  A point that
    cannot be resolved by its content ID, or whose stored text has changed,
    is not admissible evidence.
    """

    def __init__(self, retriever: QdrantSemanticRetriever, connection: Any):
        self.retriever = retriever
        self.connection = connection

    def search(self, query: str, filters: dict[str, str], limit: int) -> list[Evidence]:
        accepted: list[Evidence] = []
        # Ask the vector store for a modest surplus because stale points may be
        # rejected during canonical resolution.
        for evidence in self.retriever.search(query, filters, max(limit * 3, limit)):
            content_id = str(evidence.metadata.get("content_unit_id") or evidence.source_id)
            row = self.connection.execute(
                "SELECT canonical_text FROM canonical_content WHERE content_id = ?",
                (content_id,),
            ).fetchone()
            if row is None:
                continue
            canonical_text = row["canonical_text"] if isinstance(row, dict) else row[0]
            if canonical_text != evidence.evidence:
                continue
            accepted.append(evidence)
            if len(accepted) >= limit:
                break
        return accepted
