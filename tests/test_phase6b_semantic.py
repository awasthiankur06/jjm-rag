from jjm_rag.semantic.candidates import deterministic_candidate_id, select_semantic_candidates
from jjm_rag.semantic.contracts import SemanticDocument
from jjm_rag.semantic.index import InMemorySemanticIndex


def test_candidate_selection_excludes_structured_and_low_information_units():
    candidates, decisions = select_semantic_candidates([
        {"content_id": "page-1", "canonical_text": "The mission provides reliable drinking water to rural households.", "content_type": "page", "production_included": True},
        {"content_id": "cell-1", "canonical_text": "98.50%", "content_type": "cell", "production_included": True},
        {"content_id": "excluded", "canonical_text": "Corrupted source text with enough length to pass.", "content_type": "page", "filename": "Status of Pipe Water Supply in School (2).xls", "production_included": False},
        {"content_id": "empty", "canonical_text": "", "content_type": "page", "production_included": True},
    ])
    assert [item["content_id"] for item in candidates] == ["page-1"]
    assert {decision.reason for decision in decisions} == {"eligible", "structured_unit", "excluded_source", "empty_text"}


def test_candidate_identity_is_deterministic_and_model_records_are_separate():
    assert deterministic_candidate_id("page-1", "text") == deterministic_candidate_id("page-1", "text")
    record = SemanticDocument("content-1", "doc-1", "version-1", "text", "hash", "a.pdf", "policy", "policy")
    assert record.model_name == "UNEMBEDDED"
    assert record.content_id == "content-1"


def test_semantic_index_is_idempotent_and_model_partitioned():
    index = InMemorySemanticIndex()
    first = SemanticDocument("content-1", "doc-1", "version-1", "text", "hash", "a.pdf", "policy", "policy", model_name="model-a", model_version="1")
    second = SemanticDocument("content-1", "doc-1", "version-1", "text", "hash", "a.pdf", "policy", "policy", model_name="model-b", model_version="1")
    assert index.upsert([first], [[1.0, 0.0]]) == 1
    assert index.upsert([first], [[1.0, 0.0]]) == 1
    assert index.upsert([second], [[0.0, 1.0]]) == 1
    assert index.count() == 2
    assert index.count(model_name="model-a") == 1
    assert index.search([1.0, 0.0], filters={"missing": "value"}) == []
