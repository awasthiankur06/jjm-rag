from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class Evidence:
    source_id: str
    filename: str
    location: dict[str, Any]
    retrieval_method: str
    relevance: float
    evidence: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def display(self) -> str:
        return self.evidence


@dataclass
class QueryRoute:
    query_type: str
    strategies: list[str]
    filters: dict[str, str]
    entities: list[str]
    reason: str
    confidence: float
    uncertainty: list[str] = field(default_factory=list)


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> Any:
        ...


class VectorIndex(Protocol):
    def search(self, query: str, top_k: int = 10) -> list[Evidence]:
        ...


class StructuredStore(Protocol):
    def query(self, query: str, filters: dict[str, str] | None = None) -> list[Evidence]:
        ...


class ExactRetriever(Protocol):
    def search(self, query: str, top_k: int = 10) -> list[Evidence]:
        ...


class SemanticRetriever(Protocol):
    def search(self, query: str, top_k: int = 10) -> list[Evidence]:
        ...


class EvidenceFusion(Protocol):
    def fuse(self, results: list[list[Evidence]], top_k: int = 10) -> list[Evidence]:
        ...


class QueryRouter(Protocol):
    def route(self, query: str) -> QueryRoute:
        ...
