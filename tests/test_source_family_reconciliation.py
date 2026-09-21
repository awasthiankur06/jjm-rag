from jjm_rag.evaluation.source_family_reconciliation import allows_automatic_logical_consolidation, classify_members
from jjm_rag.production.rag import RagService


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
