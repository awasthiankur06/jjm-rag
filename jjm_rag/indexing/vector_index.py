from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class VectorRecord:
    id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


class InMemoryVectorIndex:
    """Simple in-memory vector store shim for the Phase 1 foundation."""

    def __init__(self):
        self.records: list[VectorRecord] = []

    def add(self, record: VectorRecord) -> None:
        self.records.append(record)

    def search(self, query: str, limit: int = 5) -> list[VectorRecord]:
        q = query.lower()
        scored = []
        for record in self.records:
            score = 0
            if q in record.text.lower():
                score += 10
            for token in q.split():
                if token.lower() in record.text.lower():
                    score += 1
            scored.append((score, record))
        return [record for _, record in sorted(scored, reverse=True)[:limit]]
