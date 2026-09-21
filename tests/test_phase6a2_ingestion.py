import json
from pathlib import Path

from jjm_rag.ingestion.canonical_persistence import backfill_row_geography, parse_source, persist_canonical_source
from jjm_rag.ingestion.format_detection import detect_format
from jjm_rag.persistence.database import apply_migration, sqlite_connection, transaction


ROOT = Path(__file__).resolve().parents[1]


def _connection():
    connection = sqlite_connection(":memory:")
    apply_migration(connection, ROOT / "db" / "migrations" / "001_initial_schema.sql")
    return connection


def test_parser_canonical_persistence_dimensions_observations_and_audit(tmp_path):
    source = tmp_path / "Coverage Format C17A.xls"
    source.write_text(
        """<html><body><table>
        <tr><th>State</th><th>District</th><th>Coverage (%)</th></tr>
        <tr><td>Assam</td><td>Kamrup</td><td>98.50%</td></tr>
        <tr><td>Assam</td><td>Barpeta</td><td>----</td></tr>
        </table></body></html>""",
        encoding="utf-8",
    )
    connection = _connection()
    entry = {"filename": source.name, "date": "01/04/2026", "financial_year": "2025-26", "format_code": "C17A"}
    document = parse_source(source, "report", entry)
    first = persist_canonical_source(connection, document, entry, "execution-1")

    assert first["status"] == "SUCCESS"
    assert first["records"] == 6
    assert connection.execute("SELECT COUNT(*) FROM geography_dimensions").fetchone()[0] == 2
    assert connection.execute("SELECT COUNT(*) FROM reporting_dimensions").fetchone()[0] == 1
    assert connection.execute("SELECT COUNT(*) FROM ingestion_audit").fetchone()[0] == 1
    assert connection.execute("SELECT COUNT(*) FROM canonical_content WHERE content_type = 'row'").fetchone()[0] == 2
    numeric = connection.execute("SELECT value_raw, value_numeric, unit, normalization_status FROM observations WHERE value_raw = '98.50%'").fetchone()
    assert numeric[0] == "98.50%"
    assert numeric[1] == 98.5
    assert numeric[2] == "%"
    ambiguous = connection.execute("SELECT value_numeric, normalization_status FROM observations WHERE value_raw = '----'").fetchone()
    assert ambiguous[0] is None
    assert ambiguous[1] == "RAW_AMBIGUOUS"
    provenance = connection.execute("SELECT table_name, row_index, column_index, cell_reference FROM provenance_records WHERE table_name = 'Table 1' AND row_index = 1 AND column_index = 2").fetchone()
    assert tuple(provenance) == ("Table 1", 1, 2, "R2C3")

    second = persist_canonical_source(connection, document, entry, "execution-2")
    assert second["status"] == "ALREADY_INGESTED"
    assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
    assert connection.execute("SELECT COUNT(*) FROM structured_records").fetchone()[0] == 6
    assert connection.execute("SELECT COUNT(*) FROM ingestion_audit").fetchone()[0] == 2

    header_path = connection.execute("SELECT header_path FROM structured_records WHERE value_raw = '98.50%' LIMIT 1").fetchone()
    assert header_path is not None
    assert 'Coverage (%)' in str(header_path[0])


def test_html_and_pdf_metadata_preserve_structure_without_changing_numeric_values(tmp_path):
    html_source = tmp_path / "Coverage Format C17A.xls"
    html_source.write_text(
        """<html><body><table>
        <tr><th rowspan='2'>State</th><th colspan='2'>FHTCs</th></tr>
        <tr><th>Coverage (in %)</th><th>Coverage (in Nos.)</th></tr>
        <tr><td>Assam</td><td>98.50%</td><td>12345</td></tr>
        </table></body></html>""",
        encoding="utf-8",
    )
    connection = _connection()
    entry = {"filename": html_source.name, "date": "01/04/2026", "financial_year": "2025-26", "format_code": "C17A"}
    document = parse_source(html_source, "report", entry)
    persist_canonical_source(connection, document, entry, "execution-html")

    row = connection.execute("SELECT metric_name, value_numeric, unit, header_path FROM structured_records WHERE value_raw = '98.50%' LIMIT 1").fetchone()
    assert row[0] == "Coverage (in %)"
    assert row[1] == 98.5
    assert row[2] == "%"
    header_path = str(row[3])
    assert 'FHTCs' in header_path
    assert 'Coverage (in %)' in header_path
    assert header_path.startswith('["FHTCs"')

    pdf_source = ROOT / "knowlade base files" / "Operational-Guidelines-JJM-2.pdf"
    pdf_document = parse_source(pdf_source, "policy", {"filename": pdf_source.name})
    assert len(pdf_document.sections) >= 1
    assert pdf_document.sections[0].title.startswith("Page ")
    assert pdf_document.source_metadata.parser_name == "pdf_parser"

    xlsx_path = tmp_path / "sample.xlsx"
    xlsx_path.write_bytes(b"PK\x03\x04fake-zip")
    assert detect_format(xlsx_path).format_name == "xlsx"


def test_html_table_keeps_geography_header_and_excludes_numeric_total_row_from_headers(tmp_path):
    source = tmp_path / "coverage.xls"
    source.write_text(
        """<table>
        <tr><th rowspan='2'>S. No.</th><th rowspan='2'>State/ UT</th><th colspan='2'>Completion</th></tr>
        <tr><th>Total schemes</th><th>Physically completed</th></tr>
        <tr><th>Total</th><th>Total</th><th>641995</th><th>377791</th></tr>
        <tr><td>1</td><td>Assam</td><td>100</td><td>90</td></tr>
        </table>""",
        encoding="utf-8",
    )

    table = parse_source(source, "report", {"filename": source.name}).tables[0]
    assert table.headers == ["col_1", "State/ UT", "Total schemes", "Physically completed"]
    assert "641995" not in table.headers
    assert table.rows[0] == ["Total", "Total", "641995", "377791"]


def test_metric_names_containing_state_or_district_do_not_overwrite_geography(tmp_path):
    source = tmp_path / "water_quality.xls"
    source.write_text(
        """<table><tr><th>S. No.</th><th>State/ UT</th><th>No. of NABL accredited State Referral Lab</th><th>No. of districts with access to NABL accredited lab</th></tr>
        <tr><td>5</td><td>Bihar</td><td>33</td><td>754</td></tr></table>""",
        encoding="utf-8",
    )
    connection = _connection()
    document = parse_source(source, "report", {"filename": source.name})
    persist_canonical_source(connection, document, {"filename": source.name}, "geography-test")
    states = [row[0] for row in connection.execute("SELECT DISTINCT state_name FROM geography_dimensions")]
    assert states == ["Bihar"]


def test_multilevel_table_state_name_is_carried_to_every_metric_in_the_row(tmp_path):
    """A report may use ``State Name`` and a three-level metric header."""
    source = tmp_path / "habitation_coverage.xls"
    source.write_text(
        """<table>
        <tr><th rowspan='3'>S.No.</th><th rowspan='3'>State Name</th><th rowspan='3'>Total Habitations</th><th colspan='3'>PWS Habitations</th></tr>
        <tr><th colspan='3'>With FHTC Coverage >=75 and &lt;100 %</th></tr>
        <tr><th>Habs</th><th>House Holds</th><th>House Connectons</th></tr>
        <tr><td>14</td><td>Karnataka</td><td>57879</td><td>3395</td><td>644707</td><td>406979</td></tr>
        </table>""",
        encoding="utf-8",
    )
    connection = _connection()
    document = parse_source(source, "report", {"filename": source.name})
    persist_canonical_source(connection, document, {"filename": source.name}, "state-name-test")

    rows = connection.execute(
        """SELECT sr.value_raw, gd.state_name, sr.header_path
           FROM structured_records sr
           JOIN geography_dimensions gd ON gd.geography_id = sr.geography_id
           WHERE sr.metric_name = 'House Connectons'"""
    ).fetchall()
    assert len(rows) == 1
    assert tuple(rows[0][:2]) == ("406979", "Karnataka")
    assert json.loads(rows[0][2]) == [
        "PWS Habitations",
        "With FHTC Coverage >=75 and <100 %",
        "House Connectons",
    ]


def test_legacy_state_name_rows_can_be_relinked_without_reingestion(tmp_path):
    source = tmp_path / "legacy_state_name.xls"
    source.write_text(
        """<table><tr><th>State Name</th><th>Metric</th></tr>
        <tr><td>Karnataka</td><td>42</td></tr></table>""",
        encoding="utf-8",
    )
    connection = _connection()
    document = parse_source(source, "report", {"filename": source.name})
    result = persist_canonical_source(connection, document, {"filename": source.name}, "legacy-state-name")
    connection.execute("UPDATE structured_records SET geography_id = NULL WHERE document_id = ?", (result["document_id"],))

    repaired = backfill_row_geography(connection, {str(result["document_id"])})
    assert repaired["source_rows"] == 1
    assert repaired["structured_records_relinked"] == 2
    states = [row[0] for row in connection.execute("SELECT DISTINCT state_name FROM geography_dimensions")]
    assert states == ["Karnataka"]


def test_numeric_or_total_dimension_cells_are_not_geography(tmp_path):
    source = tmp_path / "dimension_guard.xls"
    source.write_text(
        """<table><tr><th>S. No.</th><th>State/ UT</th><th>Metric</th></tr>
        <tr><td>1</td><td>Assam</td><td>10</td></tr>
        <tr><td>Total</td><td>Total</td><td>10</td></tr>
        <tr><td>2</td><td>33</td><td>10</td></tr></table>""",
        encoding="utf-8",
    )
    connection = _connection()
    document = parse_source(source, "report", {"filename": source.name})
    persist_canonical_source(connection, document, {"filename": source.name}, "dimension-guard-test")
    states = [row[0] for row in connection.execute("SELECT DISTINCT state_name FROM geography_dimensions WHERE state_name IS NOT NULL")]
    assert states == ["Assam"]
    assert connection.execute("SELECT COUNT(*) FROM structured_records WHERE metric_name LIKE 'col_%'").fetchone()[0] == 0


def test_excluded_source_remains_out_of_production_manifest():
    manifest = json.loads((ROOT / "artifacts/corpus_manifest_final.json").read_text(encoding="utf-8"))
    excluded = next(item for item in manifest["files"] if item["filename"] == "Status of Pipe Water Supply in School (2).xls")
    assert excluded["production_decision"] == "EXCLUDED_CORRUPTED_SOURCE"
    assert excluded["quality_state"] == "BLOCKED"
    assert excluded["filename"] not in {item["filename"] for item in manifest["files"] if item.get("production_decision") != "EXCLUDED_CORRUPTED_SOURCE"}


def test_source_transaction_rolls_back_partial_document_on_persistence_failure():
    connection = _connection()

    try:
        with transaction(connection) as session:
            session.execute(
                "INSERT INTO documents (document_id, filename, sha256, ingestion_status, production_included) VALUES (?, ?, ?, ?, ?)",
                ("partial-document", "partial.xls", "partial-sha", "INGESTED", True),
            )
            session.execute(
                "INSERT INTO document_versions (version_id, document_id, content_hash) VALUES (?, ?, ?)",
                ("invalid-version", "missing-document", "hash"),
            )
    except Exception:
        pass
    else:
        raise AssertionError("invalid foreign key must fail")

    assert connection.execute("SELECT COUNT(*) FROM documents WHERE document_id = ?", ("partial-document",)).fetchone()[0] == 0
