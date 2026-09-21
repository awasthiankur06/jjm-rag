from jjm_rag.evaluation.source_family_reconciliation import classify_members


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


def test_conflicting_same_scope_members_stay_separate():
    left = member("one.xls", {"assam"}, {"total"}, {("assam", "total"): {"10"}})
    right = member("two.xls", {"assam"}, {"total"}, {("assam", "total"): {"11"}})
    result = classify_members("Test report", [left, right])
    assert result["consolidation_decision"] == "KEEP_SEPARATE_CONFLICTING_SNAPSHOTS"
