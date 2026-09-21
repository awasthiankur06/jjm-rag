from jjm_rag.production.rag import GroundingValidator, RagService
from jjm_rag.retrieval.interfaces import Evidence


class Store:
    def exact(self, query, limit):
        return [Evidence("content-1", "CS1 A. Coverage.xls", {"page": 1}, "exact", 1.0, "FHTC coverage fields", {"document_id": "doc-1", "provenance_id": "prov-1"})]

    def lexical(self, query, limit):
        return []

    def structured(self, query, filters, limit):
        return [Evidence("content-2", "CS1 A. Coverage.xls", {"row": 2}, "structured", 0.95, "FHTC coverage: 98.5", {"document_id": "doc-1", "provenance_id": "prov-2", "value_numeric": 98.5})]


class Semantic:
    def search(self, query, filters, limit):
        return []


class LLM:
    def __init__(self, text):
        self.text = text

    def generate(self, system, user, *, max_tokens, temperature):
        assert "only from the supplied evidence" in system
        assert "FHTC" in user
        return {"text": self.text}


def test_grounded_generation_has_deterministic_metadata_and_canonical_ids():
    response = RagService(Store(), semantic=Semantic(), llm=LLM("The coverage is 98.5 [1].")).query("What is the FHTC coverage?")
    assert response.confidence["grounded"] is True
    assert response.confidence["evidence_count"] == 2
    assert response.confidence["source_count"] == 1
    assert response.citations[0]["content_unit_id"] in {"content-1", "content-2"}


def test_fabricated_citation_is_rejected():
    response = RagService(Store(), llm=LLM("The answer is 42 [99].")).query("What is the FHTC coverage?")
    assert response.confidence["grounded"] is False
    assert "citation outside returned evidence" in " ".join(response.warnings)


def test_insufficient_evidence_is_controlled():
    class EmptyStore(Store):
        def exact(self, query, limit): return []
        def structured(self, query, filters, limit): return []

    response = RagService(EmptyStore(), llm=LLM("I could not find sufficient evidence in the available JJM corpus to answer this reliably.")).query("What is the moon made of?")
    assert response.confidence["grounded"] is False
    assert response.citations == []


def test_partial_semantic_index_falls_back_to_postgres_evidence():
    response = RagService(Store(), semantic=Semantic()).query("What is the FHTC coverage?", retrieval_only=True)
    assert response.evidence
    assert all(item["retrieval_method"] != "semantic" for item in response.evidence)
    assert response.retrieval["candidate_count"] >= 1


def test_excluded_source_is_never_returned():
    class ExcludedStore(Store):
        def exact(self, query, limit):
            return [Evidence("excluded", "Status of Pipe Water Supply in School (2).xls", {}, "exact", 1.0, "excluded", {})]
        def structured(self, query, filters, limit): return []

    response = RagService(ExcludedStore()).query("school water supply", retrieval_only=True)
    assert response.evidence == []


def test_citation_validator_requires_retrieved_provenance_match():
    evidence = [Evidence("content-1", "guide.pdf", {"page": 3}, "semantic", 0.8, "guidance", {"provenance_id": "p1"})]
    valid, warnings = GroundingValidator().validate("Guidance [1]", evidence, [{"content_unit_id": "content-1", "filename": "guide.pdf", "provenance_id": "wrong"}])
    assert valid is False
    assert "provenance" in " ".join(warnings)
