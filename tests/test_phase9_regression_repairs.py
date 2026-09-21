from jjm_rag.production.rag import RagService
from jjm_rag.retrieval.interfaces import Evidence


class Store:
    def __init__(self, structured=None, lexical=None):
        self.structured_facts = structured or []
        self.lexical_facts = lexical or []

    def exact(self, query, limit): return []
    def lexical(self, query, limit): return self.lexical_facts[:limit]
    def structured(self, query, filters, limit): return self.structured_facts[:limit]


class LLM:
    def __init__(self, text): self.text = text
    def generate(self, system, user, *, max_tokens, temperature): return {"text": self.text}


def fact(source, metric, value, state, district=None, date="15/08/2019", unit=None):
    return Evidence(source, source, {}, "structured", .9, f"{metric}: {value}", {"metric_name": metric, "value_raw": str(value), "value_numeric": value, "unit": unit, "state": state, "district": district, "report_date": date, "provenance_id": f"p-{source}"})


def test_cross_document_preserves_semantic_and_structured_channels():
    store = Store([fact("report.xls", "Coverage", 90, "Assam")], [Evidence("policy", "guide.pdf", {}, "lexical", .8, "policy", {"provenance_id": "p-policy"})])
    response = RagService(store, llm=LLM("Policy and report are both supplied [1][2].")).query("What does policy say about reported coverage?")
    assert response.answer_type == "CROSS_DOCUMENT"
    assert set(response.retrieval["evidence_groups"]) == {"guide.pdf", "report.xls"}


def test_all_period_aggregation_abstains():
    facts = [fact("a", "Coverage", 80, "Assam", date="2020"), fact("b", "Coverage", 90, "Assam", date="2021")]
    response = RagService(Store(facts), llm=LLM("should not be called")).query("What is the average coverage across all reports and all reporting periods?")
    assert response.confidence["grounded"] is False
    assert response.calculation is None


def test_cross_document_missing_group_abstains():
    response = RagService(Store([fact("report.xls", "Coverage", 90, "Assam")]), llm=LLM("should not be called")).query("What does policy say about reported coverage?")
    assert response.confidence["grounded"] is False
    assert response.answer_type == "CROSS_DOCUMENT"
