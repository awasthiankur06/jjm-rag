from jjm_rag.evaluation.source_family_reconciliation import allows_automatic_logical_consolidation, classify_members
from jjm_rag.production.rag import RagService
from jjm_rag.retrieval.interfaces import Evidence


def member(filename, geography, headers, values):
    return {
        "filename": filename,
        "sha256": filename,
        "format_code": "F1",
        "signature": {
            "headers": set(headers),
            "geography": set(geography),
            "values": values,
            "structured_record_count": len(values),
        },
    }


def test_complementary_geography_members_are_logically_consolidated_not_deleted():
    left = member("assam.xls", {"assam"}, {"total"}, {("assam", "total"): {"10"}})
    right = member("maharashtra.xls", {"maharashtra"}, {"total"}, {("maharashtra", "total"): {"12"}})
    result = classify_members("Test report", [left, right])
    assert result["consolidation_decision"] == "LOGICALLY_CONSOLIDATE_ROWS_KEEP_RAW_SOURCES"
    assert result["raw_source_action"] == "RETAIN_IMMUTABLE"
    assert allows_automatic_logical_consolidation(result) is True


def test_conflicting_same_scope_members_stay_separate():
    left = member("one.xls", {"assam"}, {"total"}, {("assam", "total"): {"10"}})
    right = member("two.xls", {"assam"}, {"total"}, {("assam", "total"): {"11"}})
    result = classify_members("Test report", [left, right])
    assert result["consolidation_decision"] == "KEEP_SEPARATE_CONFLICTING_SNAPSHOTS"
    assert allows_automatic_logical_consolidation(result) is False


def test_geography_resolved_partition_does_not_require_a_physical_source_choice():
    facts = [
        {
            "filename": "assam-partition.xls",
            "metadata": {
                "document_id": "assam-document",
                "state": "Assam",
                "district": "Bajali",
                "header_path": '["Population", "TOTAL"]',
                "extracted_document_title": "District population",
            },
        }
    ]
    assert RagService._source_identity_clarification("Population for Assam", facts, []) is None


def test_district_wise_report_request_prefers_district_rows_over_state_summary():
    facts = [
        {
            "filename": "district-assam.xls",
            "metadata": {
                "document_id": "district-document",
                "state": "Assam",
                "district": "Bajali",
                "header_path": '["Number of Population", "TOTAL"]',
                "extracted_document_title": "District wise rural population",
            },
        },
        {
            "filename": "state-population.xls",
            "metadata": {
                "document_id": "state-document",
                "state": "Assam",
                "district": None,
                "header_path": '["Number of Population", "TOTAL"]',
                "extracted_document_title": "State wise rural population",
            },
        },
    ]
    query = "District wise number of Rural Population as on (01/04/2026) for Assam"
    assert RagService._requests_report_overview(query) is True
    assert RagService._source_identity_clarification(query, facts, []) is None


def test_state_wise_data_request_is_an_overview_and_lexical_noise_is_not_a_source_choice():
    query = "State wise data for Robust chlorination system Disinfection system Format"
    evidence = [
        {
            "filename": "CS1 B (ii). Robust chlorination system_ Disinfection.xls",
            "metadata": {"document_id": "chlorination", "extracted_document_title": "Robust chlorination system Disinfection system"},
        },
        {
            "filename": "JJM_Operational_Guidelines.pdf",
            "metadata": {"document_id": "guideline", "extracted_document_title": "Operational Guidelines"},
        },
    ]
    assert RagService._requests_report_overview(query) is True
    assert RagService._source_identity_clarification(query, [], evidence) is None


def test_scheme_planning_cost_status_is_a_complete_report_row_request():
    assert RagService._requests_report_overview(
        "What is the Status of Scheme Planning and Costs for Uttar Pradesh"
    ) is True


def test_geotagged_water_source_status_is_a_complete_report_row_request():
    assert RagService._requests_report_overview(
        "What is the status of geo-tagged water sources in Gujarat?"
    ) is True


def test_state_wise_overview_never_requires_a_district():
    query = "State wise data for Robust chlorination system Disinfection system"
    assert RagService._requests_report_overview(query) is True
    assert RagService._missing_required_entity(query, "FACT") is None


def test_complete_structured_overview_bypasses_generation_latency():
    class OverviewStore:
        def exact(self, query, limit):
            return []

        def lexical(self, query, limit):
            return []

        def structured(self, query, filters, limit):
            return [Evidence(
                "record-assam-installed", "chlorination.xls", {}, "structured", 1.0,
                "Installed: 73",
                {"value_numeric": 73, "value_raw": "73", "state": "Assam", "header_path": '["Robust chlorination", "Installed"]', "provenance_id": "prov-1"},
            )]

    class MustNotGenerate:
        def generate(self, *args, **kwargs):
            raise AssertionError("complete structured overview must not wait for an LLM")

    response = RagService(OverviewStore(), llm=MustNotGenerate()).query(
        "State wise data for Robust chlorination system Disinfection system"
    )
    assert response.answer.startswith("Here is the available report summary:")
    assert "Assam" in response.answer
    assert "73" in response.answer
    assert "returned validated structured report overview without generation" in response.warnings
