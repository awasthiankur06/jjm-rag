from jjm_rag.production.postgres_store import PostgresEvidenceStore


def test_report_title_words_are_not_treated_as_unknown_geography():
    store = object.__new__(PostgresEvidenceStore)
    store._geography_names = lambda: (["Assam"], ["Baksa"])
    assert store._has_unresolved_named_entity(
        "What is the total House connections as on 23/08/2026 for Assam in the Progress in Aspirational districts report?"
    ) is False


def test_explicit_unknown_state_value_remains_blocked():
    store = object.__new__(PostgresEvidenceStore)
    store._geography_names = lambda: (["Assam"], ["Baksa"])
    assert store._has_unresolved_named_entity("What is the coverage for state: Imaginaryland?") is True


def test_column_header_date_overrides_less_specific_report_date():
    row = {
        "content_id": "record-1", "filename": "Progress in Aspirational districts.xls", "table_name": "Table 1", "page_number": None, "sheet_name": None,
        "row_index": 2, "column_index": 5, "cell_reference": "R2C5", "provenance_id": "prov-1",
        "record_id": "record-1", "document_id": "doc-1", "metric_name": "House connections as on 23/08/2026",
        "header_path": '["House connections as on 23/08/2026"]', "extracted_document_title": "Progress report",
        "format_code": "P3", "relevance_score": 1, "value_raw": "120939", "state_name": "Assam",
        "district_name": "Baksa", "report_date": "15/08/2019", "reporting_period": None,
        "financial_year": None, "value_numeric": 120939, "unit": None,
    }
    assert PostgresEvidenceStore._structured_evidence(row).metadata["report_date"] == "23/08/2026"
