from pathlib import Path

from jjm_rag.ingestion.canonical_persistence import parse_source, persist_canonical_source
from jjm_rag.persistence.database import apply_migration, sqlite_connection


ROOT = Path(__file__).resolve().parents[1]


def test_selected_state_parameter_is_applied_to_division_rows(tmp_path):
    source = tmp_path / "progress_tracker.xls"
    source.write_text(
        """<html><body><span class='SelectedParameter'>State: Maharashtra</span>
        <table><tr><th>S. No.</th><th>Division</th><th>Total schemes</th></tr>
        <tr><td>1</td><td>Pune</td><td>12</td></tr></table></body></html>""",
        encoding="utf-8",
    )
    conn = sqlite_connection(":memory:")
    apply_migration(conn, ROOT / "db" / "migrations" / "001_initial_schema.sql")
    document = parse_source(source, "report", {"filename": source.name, "extracted_document_title": "Progress tracker", "title_confidence": "HIGH"})
    persist_canonical_source(conn, document, {"filename": source.name, "extracted_document_title": "Progress tracker", "title_confidence": "HIGH"}, "selected-state")
    row = conn.execute("SELECT gd.state_name, gd.division_name FROM structured_records sr JOIN geography_dimensions gd ON gd.geography_id=sr.geography_id WHERE sr.metric_name='Total schemes'").fetchone()
    assert tuple(row) == ("Maharashtra", "Pune")
