from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RetrievalCandidate:
    source: str
    score: float
    strategy: str
    metadata: dict[str, str] = field(default_factory=dict)


class HybridRetriever:
    """Candidate fusion layer for exact, semantic, and structured retrieval outputs."""

    def fuse(self, exact_hits: list[RetrievalCandidate], semantic_hits: list[RetrievalCandidate], structured_hits: list[RetrievalCandidate]) -> list[RetrievalCandidate]:
        merged = {candidate.source: candidate for candidate in exact_hits + semantic_hits + structured_hits}
        fused = list(merged.values())
        return sorted(fused, key=lambda c: c.score, reverse=True)
