from pathlib import Path

import pytest

from jjm_rag.production.cloud_indexing import dry_run, load_candidates
from jjm_rag.production.qdrant import CanonicalValidatedQdrantRetriever, QdrantCloudStore
from jjm_rag.retrieval.interfaces import Evidence
from jjm_rag.production.voyage import VoyageConfig, VoyageEmbeddingProvider
from jjm_rag.production.providers import ProviderError

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts" / "phase6b_semantic_candidate_manifest.json"


def test_dry_run_requires_exact_635_candidates_without_cloud_calls():
    result = dry_run(MANIFEST)
    assert result.status == "DRY_RUN"
    assert result.candidate_count == 635
    assert result.embedded_count == 0
    assert result.upserted_count == 0


def test_voyage_validation_rejects_wrong_dimensions_and_non_finite_values():
    with pytest.raises(ProviderError):
        VoyageEmbeddingProvider._validate([[0.0, 1.0]], 1, 1024)
    with pytest.raises(ProviderError):
        VoyageEmbeddingProvider._validate([[float("nan")] * 1024], 1, 1024)


def test_voyage_requires_cloud_configuration_and_uses_expected_defaults():
    provider = VoyageEmbeddingProvider(VoyageConfig(api_key="", batch_size=32))
    assert provider.model_name == "voyage-4-large"
    assert provider.dimension == 1024
    with pytest.raises(ProviderError):
        provider.embed_query("test")


def test_qdrant_point_id_is_deterministic_and_configuration_is_explicit():
    store = QdrantCloudStore(url="", api_key="", collection="")
    assert store.point_id("content-1") == store.point_id("content-1")
    assert store.configured is False


def test_qdrant_results_must_match_current_canonical_content():
    class Retriever:
        def search(self, query, filters, limit):
            return [
                Evidence("current", "source.xls", {}, "semantic", 1.0, "current text", {"content_unit_id": "current"}),
                Evidence("stale", "source.xls", {}, "semantic", 0.9, "old text", {"content_unit_id": "stale"}),
                Evidence("missing", "source.xls", {}, "semantic", 0.8, "missing text", {"content_unit_id": "missing"}),
            ]

    class Connection:
        def execute(self, query, params):
            values = {"current": {"canonical_text": "current text"}, "stale": {"canonical_text": "new text"}}
            class Result:
                def fetchone(self):
                    return values.get(params[0])
            return Result()

    result = CanonicalValidatedQdrantRetriever(Retriever(), Connection()).search("question", {}, 10)
    assert [item.source_id for item in result] == ["current"]
