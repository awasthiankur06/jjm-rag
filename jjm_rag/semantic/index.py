from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from .contracts import SemanticDocument


@dataclass(frozen=True)
class IndexedSemanticRecord:
    record: SemanticDocument
    vector: tuple[float, ...]


class InMemorySemanticIndex:
    """Model-partitioned prototype used when pgvector is unavailable."""

    def __init__(self):
        self._records: dict[tuple[str, str | None, str], IndexedSemanticRecord] = {}

    def upsert(self, records: Sequence[SemanticDocument], vectors: Sequence[Sequence[float]]) -> int:
        if len(records) != len(vectors):
            raise ValueError("records and vectors must have equal length")
        for record, vector in zip(records, vectors):
            key = (record.model_name, record.model_version, record.content_id)
            self._records[key] = IndexedSemanticRecord(record, tuple(float(value) for value in vector))
        return len(records)

    def count(self, *, model_name: str | None = None, model_version: str | None = None) -> int:
        return sum(
            (model_name is None or key[0] == model_name)
            and (model_version is None or key[1] == model_version)
            for key in self._records
        )

    def search(self, query_vector: Sequence[float], *, limit: int = 10, filters: dict[str, Any] | None = None) -> list[SemanticDocument]:
        query = tuple(float(value) for value in query_vector)
        scored: list[tuple[float, SemanticDocument]] = []
        for item in self._records.values():
            if filters and any(item.record.geography.get(key) != value and item.record.reporting.get(key) != value for key, value in filters.items()):
                continue
            if len(query) != len(item.vector):
                continue
            score = sum(left * right for left, right in zip(query, item.vector))
            scored.append((score, item.record))
        return [record for _, record in sorted(scored, key=lambda pair: (-pair[0], pair[1].content_id))[:limit]]
