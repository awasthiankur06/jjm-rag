import json
from pathlib import Path

from jjm_rag.persistence.database import sqlite_connection

ROOT = Path('d:/jjm-rag')


def test_schema_is_created_for_phase6a_models():
    conn = sqlite_connection(':memory:')
    sql = (ROOT / 'db/migrations/001_initial_schema.sql').read_text(encoding='utf-8')
    conn.executescript(sql)
    tables = {
        row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    required = {
        'documents',
        'document_versions',
        'provenance_records',
        'geography_dimensions',
        'reporting_dimensions',
        'structured_records',
        'observations',
        'canonical_content',
        'ingestion_audit',
    }
    assert required.issubset(tables)
    conn.close()


def test_excluded_corrupted_source_stays_out_of_production_records():
    manifest = json.loads((ROOT / 'artifacts/corpus_manifest_final.json').read_text(encoding='utf-8'))
    excluded = next(
        record for record in manifest['files']
        if record['filename'] == 'Status of Pipe Water Supply in School (2).xls'
    )
    assert excluded['production_decision'] == 'EXCLUDED_CORRUPTED_SOURCE'
    assert excluded['ingestion_status'] == 'EXCLUDED_CORRUPTED_SOURCE'
    assert excluded['quality_state'] == 'BLOCKED'
    assert excluded['sha256'] == 'bf4eafc15390dd98688a2f0306f28457a60bc027343e5346a0bc3be2d4009ee3'


def test_cli_dry_run_summary_excludes_corrupted_source():
    from jjm_rag.ingestion.cli import _process_manifest

    result = _process_manifest(ROOT / 'artifacts/corpus_manifest_final.json', dry_run=True)
    assert result['mode'] == 'dry-run'
    assert result['summary']['files_excluded'] == 1
    assert 'Status of Pipe Water Supply in School (2).xls' not in result['eligible_files']
