from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol, Sequence


@dataclass(frozen=True)
class SemanticDocument:
    """Model-specific index record; canonical PostgreSQL data remains authoritative."""

    content_id: str
    document_id: str
    version_id: str | None
    text: str
    content_hash: str
    source_filename: str
    source_family: str | None
    report_type: str | None
    geography: dict[str, str | None] = field(default_factory=dict)
    reporting: dict[str, str | None] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    model_name: str = "UNEMBEDDED"
    model_version: str | None = None
    embedding_provider: str = "unknown"
    embedding_dimension: int | None = None
    indexed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EmbeddingProvider(Protocol):
    model_name: str
    model_version: str | None
    dimension: int

    def embed(self, texts: Sequence[str]) -> Any:
        """Return one vector per input text without mutating canonical data."""
        ...


class SemanticIndex(Protocol):
    def upsert(self, records: Sequence[SemanticDocument]) -> int:
        ...

    def search(self, query_vector: Any, *, limit: int = 10, filters: dict[str, Any] | None = None) -> list[SemanticDocument]:
        ...

    def count(self, *, model_name: str | None = None, model_version: str | None = None) -> int:
        ...
