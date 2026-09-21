"""Replaceable semantic indexing contracts and deterministic candidate selection."""

from .contracts import EmbeddingProvider, SemanticDocument, SemanticIndex
from .candidates import CandidateDecision, select_semantic_candidates
from .index import InMemorySemanticIndex

__all__ = [
    "EmbeddingProvider",
    "SemanticDocument",
    "SemanticIndex",
    "InMemorySemanticIndex",
    "CandidateDecision",
    "select_semantic_candidates",
]
