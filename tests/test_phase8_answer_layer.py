from jjm_rag.production.rag import RagService
from jjm_rag.retrieval.interfaces import Evidence


class FactStore:
    def __init__(self, facts):
        self.facts = facts

    def exact(self, query, limit):
        return []

    def lexical(self, query, limit):
        return []

    def structured(self, query, filters, limit):
        return self.facts[:limit]


class LLM:
    def __init__(self, text):
        self.text = text

    def generate(self, system, user, *, max_tokens, temperature):
        assert "STRUCTURED FACT" in user or "VERIFIED DETERMINISTIC RESULT" in user
        return {"text": self.text}


def fact(source, metric, value, state, district=None, date="15/08/2019", unit=None):
    return Evidence(source, "Progress at district level.xls", {"row": 1}, "structured", .95, f"{metric}: {value}", {"document_id": "doc-1", "provenance_id": f"prov-{source}", "metric_name": metric, "value_raw": str(value), "value_numeric": value, "unit": unit, "state": state, "district": district, "report_date": date, "reporting_period": None, "financial_year": None})


def test_structured_fact_preserves_typed_metadata_and_answer_type():
    response = RagService(FactStore([fact("a", "Total Households", 614994, "Kerala", "Thrissur")]), llm=LLM("There were 614994 households [1].")).query("How many households were reported for Thrissur in Kerala?")
    assert response.answer_type == "FACT"
    assert response.confidence["grounded"] is True
    assert response.structured_facts[0]["metadata"]["district"] == "Thrissur"
    assert response.structured_facts[0]["metadata"]["value_numeric"] == 614994


def test_difference_is_deterministic_and_sent_to_generation():
    facts = [fact("a", "Total Households", 614994, "Kerala", "Thrissur"), fact("b", "Total Households", 368267, "Madhya Pradesh", "Balaghat")]
    response = RagService(FactStore(facts), llm=LLM("The difference is 999 [1].")).query("What is the difference between Thrissur and Balaghat households?")
    assert response.answer_type == "CALCULATION"
    assert response.calculation["result"] == 246727
    assert "246727" in response.answer
    assert response.calculation["inputs"][0]["provenance_id"]


def test_missing_calculation_operand_abstains():
    response = RagService(FactStore([fact("a", "Total Households", 614994, "Kerala", "Thrissur")]), llm=LLM("should not be called")).query("What is the difference between Thrissur and Balaghat households?")
    assert response.confidence["grounded"] is False
    assert "sufficient structured evidence" in response.answer
    assert response.calculation is None


def test_wrong_generated_numeric_fact_is_replaced_by_validated_fact():
    response = RagService(FactStore([fact("a", "FHTC coverage", 100, "Telangana", "Khammam", unit="%")]), llm=LLM("The coverage was 12 [1].")).query("What was the FHTC coverage for Khammam in Telangana?")
    assert "100" in response.answer
    assert response.confidence["grounded"] is True


def test_incompatible_metrics_are_not_calculated():
    facts = [fact("a", "Total Households", 614994, "Kerala", "Thrissur"), fact("b", "FHTC coverage", 99.38, "Madhya Pradesh", "Balaghat", unit="%")]
    response = RagService(FactStore(facts), llm=LLM("should not be called")).query("What is the difference between Thrissur households and Balaghat coverage?")
    assert response.confidence["grounded"] is False
    assert response.calculation is None


def test_cross_document_selection_preserves_source_groups():
    facts = [fact("a", "Total Households", 614994, "Kerala", "Thrissur")]
    class CrossStore(FactStore):
        def lexical(self, query, limit):
            return [Evidence("policy", "guideline.pdf", {}, "lexical", .8, "policy evidence", {"provenance_id": "p-policy"})]

    response = RagService(CrossStore(facts), llm=LLM("The policy and reported fact are related [1][2].")).query("According to the guidance, how does policy relate to the reported households?")
    assert response.answer_type == "CROSS_DOCUMENT"
    assert set(response.retrieval["evidence_groups"]) == {"guideline.pdf", "Progress at district level.xls"}


def test_latest_without_report_date_abstains():
    response = RagService(FactStore([fact("a", "Total Households", 10, "Kerala", "Thrissur", date=None)]), llm=LLM("should not be called")).query("What is the latest household report?")
    assert response.confidence["grounded"] is False
    assert "latest reporting snapshot" in response.answer


def test_placeholder_entity_abstains_before_structured_fact_selection():
    response = RagService(FactStore([fact("a", "PWS schemes without source", 9, "Maharashtra")])).query(
        "What is the number of PWS schemes without a source for a named state?"
    )
    assert response.answer == "Please provide the specific state needed to identify the requested record."
    assert response.structured_facts == []
    assert "missing required state" in response.warnings[0]


def test_percentage_of_total_is_deterministic_with_units():
    facts = [fact("a", "Total Households", 368267, "Madhya Pradesh", "Balaghat", unit="households"), fact("b", "Total Households", 614994, "Kerala", "Thrissur", unit="households")]
    response = RagService(FactStore(facts), llm=LLM("The share is 37.44% [1][2].")).query("What percentage of the two reported household totals is represented by Balaghat compared with Thrissur?")
    assert response.calculation["operation"] == "percentage_of_total"
    assert response.calculation["result"] == 37.453636
    assert response.calculation["result_unit"] == "%"
    assert all(item["unit"] == "households" for item in response.calculation["inputs"])


def test_percentage_change_uses_ordered_operands():
    facts = [fact("a", "House connections", 100, "Assam", "D1", date="2020"), fact("b", "House connections", 120, "Assam", "D1", date="2021")]
    response = RagService(FactStore(facts), llm=LLM("The change is 20% [1][2].")).query("What was the percentage change in house connections between 2020 and 2021?")
    assert response.calculation["operation"] == "percentage_change"
    assert response.calculation["result"] == 20


def test_dated_state_total_sums_one_homogeneous_district_source():
    facts = [
        fact("a", "House connections as on 23/08/2026", 120939, "Assam", "Baksa", date=None),
        fact("b", "House connections as on 23/08/2026", 258624, "Assam", "Barpeta", date=None),
    ]
    response = RagService(FactStore(facts), llm=LLM("The total is 379563 [1][2].")).query(
        "What is the total House connections as on 23/08/2026 for Assam in the report?"
    )
    assert response.answer_type == "CALCULATION"
    assert response.calculation["operation"] == "sum"
    assert response.calculation["result"] == 379563
    assert len(response.calculation["inputs"]) == 2


def test_dated_state_total_does_not_mix_sources():
    first = fact("a", "House connections as on 23/08/2026", 120939, "Assam", "Baksa", date=None)
    second = Evidence("b", "Other report.xls", {"row": 2}, "structured", .95, "House connections: 258624", {**fact("b", "House connections as on 23/08/2026", 258624, "Assam", "Barpeta", date=None).metadata, "document_id": "doc-2"})
    response = RagService(FactStore([first, second]), llm=LLM("should not be called")).query(
        "What is the total House connections as on 23/08/2026 for Assam?"
    )
    assert response.calculation is None


def test_validated_calculation_does_not_require_generation_provider():
    facts = [
        fact("a", "House connections as on 23/08/2026", 120939, "Assam", "Baksa", date=None),
        fact("b", "House connections as on 23/08/2026", 258624, "Assam", "Barpeta", date=None),
    ]
    response = RagService(FactStore(facts)).query(
        "What is the total House connections as on 23/08/2026 for Assam in the report?"
    )
    assert response.calculation["result"] == 379563
    assert "379563" in response.answer


def test_ambiguous_dated_total_requests_report_clarification():
    first = fact("a", "House connections as on 23/08/2026", 10, "Assam", "Baksa", date=None)
    second = Evidence("b", "Other report.xls", {"row": 2}, "structured", .95, "House connections: 20", {**fact("b", "House connections as on 23/08/2026", 20, "Assam", "Barpeta", date=None).metadata, "document_id": "doc-2", "extracted_document_title": "Other report"})
    response = RagService(FactStore([first, second])).query("What is the total House connections as on 23/08/2026 for Assam?")
    assert response.clarification is not None
    assert "report/category" in response.clarification["required"]
    assert response.confidence["grounded"] is False


def test_multilevel_header_requires_source_derived_metric_choice():
    base = fact("total", "Total Habitations", 57879, "Karnataka")
    nested_one = Evidence(
        "zero-habs", "Habitation coverage.xls", {"row": 14}, "structured", .95, "Habs: 3382",
        {**fact("unused", "Habs", 3382, "Karnataka").metadata, "document_id": "j5", "extracted_document_title": "Habitation coverage", "header_path": '["PWS Habitations", "With FHTC Coverage = 0 %", "Habs"]'},
    )
    nested_two = Evidence(
        "zero-households", "Habitation coverage.xls", {"row": 14}, "structured", .95, "House Holds: 162407",
        {**fact("unused-two", "House Holds", 162407, "Karnataka").metadata, "document_id": "j5", "extracted_document_title": "Habitation coverage", "header_path": '["PWS Habitations", "With FHTC Coverage = 0 %", "House Holds"]'},
    )
    nested_three = Evidence(
        "full-connections", "Habitation coverage.xls", {"row": 14}, "structured", .95, "House Connectons: 6990630",
        {**fact("unused-three", "House Connectons", 6990630, "Karnataka").metadata, "document_id": "j5", "extracted_document_title": "Habitation coverage", "header_path": '["PWS Habitations", "With FHTC Coverage >=100 %", "House Connectons"]'},
    )
    response = RagService(FactStore([base, nested_one, nested_two, nested_three])).query("Habitation wise FHTC Coverage for Karnataka")
    assert response.clarification is not None
    assert response.clarification["required"] == ["metric/header"]
    assert "PWS Habitations → With FHTC Coverage = 0 % → Habs" in response.clarification["options"]

    selected = RagService(FactStore([base, nested_one, nested_two, nested_three])).query(
        "Habitation wise FHTC Coverage for Karnataka. Selected metric: PWS Habitations → With FHTC Coverage >=100 % → House Connectons"
    )
    assert selected.clarification is None


def test_identical_report_titles_require_physical_source_choice_before_metric_choice():
    first = Evidence("a", "quality (1).xls", {}, "structured", .95, "Habs: 0", {**fact("fa", "Habs", 0, "Maharashtra").metadata, "document_id": "one", "extracted_document_title": "Quality report", "header_path": '["Contamination", "Total", "Habs"]'})
    second = Evidence("b", "quality (2).xls", {}, "structured", .95, "Habs: 42", {**fact("fb", "Habs", 42, "Tamil Nadu").metadata, "document_id": "two", "extracted_document_title": "Quality report", "header_path": '["Contamination", "Total", "Habs"]'})
    response = RagService(FactStore([first, second])).query("Quality report total")
    assert response.clarification is not None
    assert response.clarification["required"] == ["source/report"]
    assert response.clarification["options"] == ["quality (1).xls", "quality (2).xls"]


def test_unnamed_report_with_multiple_matching_sources_requires_followup():
    first = Evidence("a", "coverage.xls", {}, "structured", .95, "Coverage: 98", {**fact("fa", "Coverage", 98, "Assam").metadata, "document_id": "one", "extracted_document_title": "Coverage report", "header_path": '["Coverage"]'})
    second = Evidence("b", "status.xls", {}, "structured", .95, "Coverage: 97", {**fact("fb", "Coverage", 97, "Assam").metadata, "document_id": "two", "extracted_document_title": "Status report", "header_path": '["Coverage"]'})
    response = RagService(FactStore([first, second])).query("What is coverage for Assam?")
    assert response.clarification is not None
    assert response.clarification["required"] == ["source/report"]


def test_shared_parent_heading_does_not_select_first_nested_metric():
    first = Evidence("a", "institutions.xls", {}, "structured", .95, "Availability: 12036", {**fact("fa", "Availability of Tap Connection", 12036, "Karnataka").metadata, "document_id": "f27", "extracted_document_title": "Institution report", "header_path": '["Nos. of Ashram Shala & Other Public Institutions", "Approved by State", "Availability of Tap Connection"]'})
    second = Evidence("b", "institutions.xls", {}, "structured", .95, "Total: 12726", {**fact("fb", "Total", 12726, "Karnataka").metadata, "document_id": "f27", "extracted_document_title": "Institution report", "header_path": '["Nos. of Ashram Shala & Other Public Institutions", "Approved by State", "Total"]'})
    third = Evidence("c", "institutions.xls", {}, "structured", .95, "Health total: 5818", {**fact("fc", "Total", 5818, "Karnataka").metadata, "document_id": "f27", "extracted_document_title": "Institution report", "header_path": '["Nos. of Health Centre", "Total"]'})
    response = RagService(FactStore([first, second, third])).query("Status of Ashram Shala & Other Public Institutions State")
    assert response.clarification is not None
    assert response.clarification["required"] == ["metric/header"]
