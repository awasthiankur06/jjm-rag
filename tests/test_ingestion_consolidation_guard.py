from jjm_rag.ingestion.cli import _manifest_consolidation_guard


def test_duplicate_hash_is_blocked_but_same_title_variants_are_retained_for_review():
    files = [
        {"filename": "one.xls", "sha256": "same", "production_decision": "INCLUDED"},
        {"filename": "two.xls", "sha256": "same", "production_decision": "INCLUDED"},
        {"filename": "three.xls", "sha256": "different", "production_decision": "INCLUDED"},
    ]
    titles = {
        "one.xls": {"extracted_document_title": "A report"},
        "two.xls": {"extracted_document_title": "A report"},
        "three.xls": {"extracted_document_title": "A report"},
    }
    guard = _manifest_consolidation_guard(files, titles)
    assert guard["exact_duplicate_hashes"] == {"same": ["one.xls", "two.xls"]}
    assert guard["repeated_title_families_retained_for_reconciliation"] == {"A report": ["one.xls", "three.xls", "two.xls"]}


def test_excluded_source_is_not_treated_as_an_ingestible_duplicate():
    guard = _manifest_consolidation_guard(
        [
            {"filename": "included.xls", "sha256": "same", "production_decision": "INCLUDED"},
            {"filename": "excluded.xls", "sha256": "same", "production_decision": "EXCLUDED_CORRUPTED_SOURCE"},
        ],
        {},
    )
    assert guard["exact_duplicate_hashes"] == {}
