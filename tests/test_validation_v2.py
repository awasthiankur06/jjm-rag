from pathlib import Path
from jjm_rag.ingestion import validation_v2


def test_suspicious_file_detected_html():
    p = Path('d:/jjm-rag/knowlade base files/Status of Pipe Water Supply in School (2).xls')
    assert p.exists()
    fmt, ev = validation_v2.detect_actual_format(str(p))
    assert fmt == 'html'


def test_html_structured_grid_present():
    base = Path('d:/jjm-rag/knowlade base files')
    html_files = list(base.glob('*.xls'))
    # find a known html-like file
    candidate = None
    for f in html_files:
        fmt, _ = validation_v2.detect_actual_format(str(f))
        if fmt == 'html':
            candidate = f
            break
    assert candidate is not None
    tables = validation_v2.parse_html_tables_structured(str(candidate))
    assert isinstance(tables, list)
    if tables:
        t = tables[0]
        assert 'num_rows' in t and t['num_rows'] > 0
        assert 'cells' in t and isinstance(t['cells'], list)


def test_operational_guidelines_scanned_pdf():
    p = Path('d:/jjm-rag/knowlade base files/Operational-Guidelines-JJM-2.pdf')
    if not p.exists():
        return
    fmt, _ = validation_v2.detect_actual_format(str(p))
    assert fmt == 'pdf'
    stats = validation_v2.analyze_pdf_full(str(p))
    # scanned or image pdf should have extraction_pct == 0
    assert stats['extraction_pct'] == 0 or stats['pages_with_text'] < stats['page_count']


def test_suspicious_file_forensic_classification_is_preserved():
    result = validation_v2.run_validation('d:/jjm-rag/knowlade base files')
    record = next(item for item in result['files'] if item['filename'] == 'Status of Pipe Water Supply in School (2).xls')
    assert record['classification'] == 'TRUNCATED_OR_CORRUPTED'
    assert record['quality_state'] == 'BLOCKED'
    assert record['production_decision'] == 'EXCLUDED_CORRUPTED_SOURCE'
    assert record['ingestion_status'] == 'EXCLUDED_CORRUPTED_SOURCE'
    assert record['exclusion_decision'] == 'SAFE_TO_EXCLUDE'
    assert record['table_count'] == 0
    assert record['sha256'] == 'bf4eafc15390dd98688a2f0306f28457a60bc027343e5346a0bc3be2d4009ee3'
    assert 'embedding' not in record
    assert 'index' not in record
    assert result['physical_corpus_count'] == 45
    assert result['production_usable_count'] == 44
    assert result['excluded_count'] == 1
    assert result['phase_1_gate'] == 'PASS_WITH_EXCLUDED_SOURCE'
