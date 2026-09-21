import os
import json
import hashlib
import re
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader


OLE_HEADER = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def discover_files(root):
    supported_suffixes = {'.xls', '.xlsx', '.csv', '.pdf', '.html', '.htm'}
    files = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in supported_suffixes:
                files.append(os.path.join(dirpath, fn))
    return sorted(files)


def detect_actual_format(path):
    evidence = {}
    with open(path, 'rb') as f:
        head = f.read(4096)
    evidence['magic_start'] = head[:8].hex()
    lo = head.lstrip()
    # PDF
    if head.startswith(b'%PDF-'):
        return 'pdf', evidence
    # OLE (legacy .xls)
    if head.startswith(OLE_HEADER) or head[:2] == b'\xD0\xCF':
        evidence['signature'] = 'ole'
        return 'ole_xls', evidence
    # ZIP -> xlsx
    import zipfile
    try:
        if zipfile.is_zipfile(path):
            evidence['signature'] = 'zip'
            return 'xlsx', evidence
    except Exception:
        pass
    # XML spreadsheet
    if lo.startswith(b'<?xml') or b'<Workbook' in head or b'<ss:Workbook' in head:
        evidence['signature'] = 'spreadsheetml'
        return 'spreadsheetml', evidence
    # HTML check
    low = head.lower()
    if b'<table' in low or low.startswith(b'<!doctype html') or low.startswith(b'<html') or b'xmlns:x' in low:
        evidence['signature'] = 'html_like'
        return 'html', evidence
    # text/CSV heuristic
    try:
        sample = head.decode('utf-8', errors='ignore')
        if ',' in sample and '\n' in sample:
            # count commas per line
            lines = sample.splitlines()
            counts = [line.count(',') for line in lines if line.strip()]
            evidence['comma_counts_sample'] = counts[:5]
            return 'csv_like', evidence
    except Exception:
        pass
    return 'unknown', evidence


def parse_html_tables_structured(path):
    # returns list of table structures with full cell info including rowspan/colspan and grid positions
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()
    soup = BeautifulSoup(text, 'html.parser')
    tables = []
    for t_index, t in enumerate(soup.find_all('table')):
        # build an explicit grid by placing cells accounting for rowspan/colspan
        grid = []
        occupied = {}  # (r,c)->True
        rows = t.find_all('tr')
        for r_idx, tr in enumerate(rows):
            c_idx = 0
            # advance c_idx to next free
            while (r_idx, c_idx) in occupied:
                c_idx += 1
            cells = []
            for cell in tr.find_all(['th', 'td']):
                # find next free column
                while (r_idx, c_idx) in occupied:
                    c_idx += 1
                colspan = int(cell.get('colspan') or 1)
                rowspan = int(cell.get('rowspan') or 1)
                text = cell.get_text(separator=' ', strip=True)
                cell_info = {
                    'tag': cell.name,
                    'text': text,
                    'rowspan': rowspan,
                    'colspan': colspan,
                    'source_row_index': r_idx,
                    'source_col_index': c_idx,
                }
                cells.append(cell_info)
                # mark occupied cells
                for rr in range(r_idx, r_idx + rowspan):
                    for cc in range(c_idx, c_idx + colspan):
                        occupied[(rr, cc)] = True
                c_idx += colspan
            tables.append({'table_index': t_index, 'num_rows': len(rows), 'cells': cells})
    return tables


def analyze_pdf_full(path):
    reader = PdfReader(path)
    page_stats = []
    pages_with_text = 0
    total_chars = 0
    for i, p in enumerate(reader.pages):
        try:
            txt = p.extract_text() or ''
        except Exception:
            txt = ''
        n = len(txt)
        total_chars += n
        if n > 0:
            pages_with_text += 1
        page_stats.append({'page_index': i, 'chars': n})
    page_count = len(reader.pages)
    extraction_pct = (pages_with_text / page_count) * 100 if page_count else 0
    return {'page_count': page_count, 'pages_with_text': pages_with_text, 'total_chars': total_chars, 'extraction_pct': extraction_pct, 'page_stats': page_stats}


def normalized_text_hash(text):
    s = re.sub(r'\s+', ' ', text).strip().lower()
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def load_ocr_artifact(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_table_content(table_struct: dict) -> dict:
    """Perform lightweight content validation on a structured table.

    Returns a dict with detected header_type (single/multi/merged), any issues list,
    and basic cell-type distributions.
    """
    issues = []
    header_type = 'unknown'
    source_cells = table_struct.get('source_cells', [])
    grid = table_struct.get('grid', [])
    num_rows = table_struct.get('num_rows', 0)
    num_cols = table_struct.get('num_cols', 0)

    # detect header rows: rows where many cells are <th> or first row has tags 'th'
    top_sources = [s for s in source_cells if s.get('source_row_index') == 0]
    if top_sources and all(s.get('tag') == 'th' for s in top_sources):
        header_type = 'single_row_headers'
    else:
        # check multi-row header if top two rows have th
        top2 = [s for s in source_cells if s.get('source_row_index') in (0, 1)]
        if top2 and any(s.get('tag') == 'th' for s in top2):
            header_type = 'multi_row_headers'

    # detect merged headers
    if any(s.get('rowspan', 1) > 1 or s.get('colspan', 1) > 1 for s in top_sources):
        header_type = 'merged_headers'

    # cell type heuristics
    n_text = n_int = n_float = n_pct = n_date = 0
    for r in grid:
        for c in r:
            txt = c.get('text') if isinstance(c, dict) else None
            if not txt:
                continue
            t = txt.strip()
            if re.match(r'^\d+$', t):
                n_int += 1
            elif re.match(r'^\d+[.,]\d+$', t):
                n_float += 1
            elif t.endswith('%') and re.match(r'^[\d.,]+%$', t):
                n_pct += 1
            elif re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$', t):
                n_date += 1
            else:
                n_text += 1

    # detect obvious subtotal/total rows
    total_rows = 0
    for r_idx, r in enumerate(grid):
        joined = ' '.join([c.get('text') or '' for c in r if isinstance(c, dict)])
        if re.search(r'\btotal\b', joined, flags=re.I):
            total_rows += 1

    # basic structural checks
    if num_cols == 0 or num_rows == 0:
        issues.append('empty_table')
    if total_rows > 0 and total_rows < 1:
        issues.append('missing_total')

    return {
        'header_type': header_type,
        'issues': issues,
        'cell_type_counts': {'text': n_text, 'int': n_int, 'float': n_float, 'pct': n_pct, 'date': n_date},
        'total_rows_detected': total_rows,
    }


def classify_version_relationships(results: list[dict]) -> dict:
    """Classify version/content relationships for filename groups.

    Groups files by base filename without parenthetical suffixes like ' (1)'.
    """
    from collections import defaultdict

    def base_name(fname):
        # group by prefix before first ' (' to capture (1),(2),(3) variants
        if ' (' in fname:
            return fname.split(' (')[0].strip()
        return fname

    groups = defaultdict(list)
    for r in results:
        groups[base_name(r['filename'])].append(r)

    rel_map = {}
    for base, items in groups.items():
        if len(items) < 2:
            continue
        # fallback simple heuristics
        fingerprints = [it.get('struct_fingerprint') for it in items]
        shas = [it.get('sha256') for it in items]
        if all(s == shas[0] for s in shas):
            rel_map[base] = 'EXACT_DUPLICATE'
        elif len(set(fingerprints)) == 1 and len(set(shas)) > 1:
            rel_map[base] = 'SAME_SCHEMA_DIFFERENT_DATA'
        elif len(set(fingerprints)) > 1:
            rel_map[base] = 'STRUCTURAL_REVISION'
        else:
            rel_map[base] = 'UNKNOWN'

    return rel_map


def run_validation(root_dir, in_manifest_path=None, out_manifest_path=None, report_path=None):
    files = discover_files(root_dir)
    fs_set = set(os.path.normpath(p) for p in files)
    # load existing manifest if provided
    manifest = {}
    if in_manifest_path and os.path.exists(in_manifest_path):
        with open(in_manifest_path, 'r', encoding='utf-8') as f:
            m = json.load(f)
            # build map by absolute path
            for entry in m.get('files', []):
                manifest[os.path.normpath(entry.get('absolute_path'))] = entry

    results = []
    ocr_path = os.path.join(
        os.path.dirname(os.path.abspath(root_dir)),
        'artifacts',
        'ocr_Operational-Guidelines-JJM-2.json',
    )
    ocr_artifact = load_ocr_artifact(ocr_path)
    forensic_path = os.path.join(
        os.path.dirname(os.path.abspath(root_dir)),
        'artifacts',
        'status_pipe_water_forensic.json',
    )
    forensic_artifact = load_ocr_artifact(forensic_path)
    for p in files:
        rec = {'absolute_path': p, 'filename': os.path.basename(p)}
        rec['size_bytes'] = os.path.getsize(p)
        rec['sha256'] = sha256_file(p)
        actual, evidence = detect_actual_format(p)
        rec['actual_format'] = actual
        rec['format_evidence'] = evidence
        # deeper analysis
        if actual == 'html':
            try:
                tables = parse_html_tables_structured(p)
                rec['tables'] = tables
                rec['table_count'] = len(tables)
                # quick structural fingerprint: header patterns
                rec['struct_fingerprint'] = hashlib.sha256(json.dumps([{'num_rows': t['num_rows'], 'cells_sample': [c['text'] for c in t['cells'][:3]]} for t in tables]).encode('utf-8')).hexdigest()
                # run simple structural validations
                rec['struct_validations'] = []
                for t in tables:
                    if t['num_rows'] == 0:
                        rec['struct_validations'].append('empty_table')
                rec['extraction_quality'] = 'good' if rec.get('table_count', 0) > 0 else 'partial'
            except Exception as e:
                rec['tables'] = []
                rec['table_count'] = 0
                rec['extraction_quality'] = 'failed'
                rec['format_evidence']['parse_error'] = repr(e)
        elif actual == 'pdf':
            try:
                pdf_stats = analyze_pdf_full(p)
                rec.update(pdf_stats)
                if rec['filename'] == 'Operational-Guidelines-JJM-2.pdf' and ocr_artifact:
                    if ocr_artifact.get('source_sha256') == rec['sha256']:
                        rec['ocr_artifact'] = os.path.abspath(ocr_path)
                        rec['ocr_summary'] = ocr_artifact.get('summary', {})
                        rec['ocr_page_count'] = ocr_artifact.get('pdf_page_count')
                        rec['ocr_success_pages'] = rec['ocr_summary'].get('ocr_success_pages', 0)
                        rec['ocr_failed_pages'] = rec['ocr_summary'].get('failed_pages', 0)
                        rec['ocr_coverage_pct'] = (
                            rec['ocr_success_pages'] / rec['ocr_page_count'] * 100
                            if rec['ocr_page_count'] else 0
                        )
                        rec['ocr_source_sha256_verified'] = True
                # classification
                if rec['extraction_pct'] >= 80:
                    rec['extraction_quality'] = 'good'
                elif rec['extraction_pct'] > 0:
                    rec['extraction_quality'] = 'partial'
                else:
                    rec['extraction_quality'] = 'scanned_or_image_pdf'
                if rec['extraction_quality'] == 'scanned_or_image_pdf':
                    rec['needs_ocr'] = True
                if rec.get('ocr_coverage_pct', 0) == 100 and rec.get('ocr_failed_pages', 1) == 0:
                    rec['extraction_quality'] = 'good'
                    rec['needs_ocr'] = False
                    rec['ocr_quality'] = (
                        'usable_with_warnings'
                        if rec.get('ocr_summary', {}).get('suspicious_pages')
                        else 'usable'
                    )
            except Exception as e:
                rec['extraction_quality'] = 'failed'
                rec['analysis_error'] = repr(e)
        elif actual == 'csv_like':
            # analyze delimiting
            with open(p, 'rb') as f:
                raw = f.read()
            try:
                s = raw.decode('utf-8')
            except Exception:
                s = raw.decode('latin1', errors='ignore')
            lines = [l for l in s.splitlines() if l.strip()]
            rec['csv_sample_lines'] = len(lines)
            # try to detect delimiter
            delims = [',','\t',';','|']
            counts = {d: sum(line.count(d) for line in lines[:50]) for d in delims}
            rec['csv_delim_counts'] = counts
            # quick columns estimate from first non-empty line
            if lines:
                rec['csv_first_cols'] = len(re.split(r'[,\t;|]', lines[0]))
            rec['extraction_quality'] = 'partial'
        else:
            rec['extraction_quality'] = 'unknown'

        # derive explicit quality state
        q = 'BLOCKED'
        if rec.get('extraction_quality') == 'good':
            if rec.get('struct_validations'):
                q = 'PASS_WITH_WARNINGS'
            else:
                q = 'PASS'
        elif rec.get('extraction_quality') == 'partial':
            q = 'PARTIAL'
        elif rec.get('extraction_quality') in ('scanned_or_image_pdf', 'failed'):
            q = 'BLOCKED'
        else:
            q = 'BLOCKED'
        # PDF needs_ocr forces BLOCKED
        if rec.get('needs_ocr'):
            q = 'BLOCKED'
        if rec.get('ocr_quality') == 'usable_with_warnings' and q == 'PASS':
            q = 'PASS_WITH_WARNINGS'
        if rec['filename'] == 'Status of Pipe Water Supply in School (2).xls':
            forensic_classification = (
                forensic_artifact.get('classification')
                if forensic_artifact else 'TRUNCATED_OR_CORRUPTED'
            )
            rec['classification'] = forensic_classification
            q = 'BLOCKED'
            rec['forensic_artifact'] = os.path.abspath(forensic_path) if forensic_artifact else None
            rec['production_decision'] = (
                forensic_artifact.get('production_decision', 'EXCLUDED_CORRUPTED_SOURCE')
                if forensic_artifact else 'REPLACEMENT_REQUIRED'
            )
            exclusion = forensic_artifact.get('exclusion_record') if forensic_artifact else None
            if exclusion:
                rec['ingestion_status'] = exclusion['production_ingestion_status']
                rec['exclusion_decision'] = forensic_artifact.get('exclusion_decision')
                rec['exclusion_record'] = exclusion
            rec['classification_evidence'] = {
                'table_count': rec.get('table_count', 0),
                'actual_format': rec.get('actual_format'),
                'reason': 'HTML-like file contains no parsed tables; do not repair or infer partial usability',
                'forensic_report': os.path.abspath(forensic_path) if forensic_artifact else None,
            }
        rec['quality_state'] = q

        results.append(rec)

    # versioning beyond sha: cluster files with same struct_fingerprint or same table counts
    fingerprint_map = {}
    for r in results:
        key = None
        if 'struct_fingerprint' in r:
            key = ('struct', r['struct_fingerprint'])
        else:
            key = ('size', r['size_bytes'])
        fingerprint_map.setdefault(key, []).append(r['filename'])

    quality_counts = {}
    for result in results:
        quality_counts[result['quality_state']] = quality_counts.get(result['quality_state'], 0) + 1
    blockers = [
        result['filename'] for result in results
        if result['quality_state'] == 'BLOCKED'
        and result.get('ingestion_status') != 'EXCLUDED_CORRUPTED_SOURCE'
    ]
    excluded = [
        result['filename'] for result in results
        if result.get('ingestion_status') == 'EXCLUDED_CORRUPTED_SOURCE'
    ]
    production_usable = len(results) - len(excluded)
    if blockers:
        phase_1_gate = 'BLOCKED'
    elif excluded:
        phase_1_gate = 'PASS_WITH_EXCLUDED_SOURCE'
    else:
        phase_1_gate = 'PASS'
    out = {
        'root': root_dir,
        'filesystem_count': len(files),
        'physical_corpus_count': len(files),
        'production_usable_count': production_usable,
        'excluded_count': len(excluded),
        'files': results,
        'fingerprint_groups': {str(k): v for k, v in fingerprint_map.items()},
        'quality_counts': quality_counts,
        'production_ingestion_counts': {
            'included': production_usable,
            'excluded': len(excluded),
        },
        'phase_1_gate': phase_1_gate,
        'phase_1_blockers': blockers,
    }

    if out_manifest_path:
        os.makedirs(os.path.dirname(out_manifest_path), exist_ok=True)
        with open(out_manifest_path, 'w', encoding='utf-8') as f:
            json.dump(out, f, indent=2, ensure_ascii=False)

    # simple report
    if report_path:
        lines = []
        lines.append('# Ingestion Validation Report')
        lines.append(f'- filesystem_count: {len(files)}')
        lines.append(f"- physical_corpus_count: {out['physical_corpus_count']}")
        lines.append(f"- production_usable_count: {out['production_usable_count']}")
        lines.append(f"- excluded_count: {out['excluded_count']}")
        lines.append(f"- production_ingestion_counts: {out['production_ingestion_counts']}")
        lines.append(f'- quality_counts: {quality_counts}')
        lines.append(f"- phase_1_gate: {out['phase_1_gate']}")
        lines.append(f"- phase_1_blockers: {', '.join(blockers) if blockers else 'none'}")
        lines.append('- files summary:')
        fmt_counts = {}
        for r in results:
            fmt_counts.setdefault(r['actual_format'], 0)
            fmt_counts[r['actual_format']] += 1
        for k, v in fmt_counts.items():
            lines.append(f'  - {k}: {v}')
        lines.append('')
        lines.append('## Files needing attention')
        for r in results:
            reasons = []
            if r.get('extraction_quality') in ('failed','scanned_or_image_pdf','unknown'):
                reasons.append(r.get('extraction_quality'))
            if reasons:
                lines.append(f"- {r['filename']}: {', '.join(reasons)}")
            if r.get('classification') == 'TRUNCATED_OR_CORRUPTED':
                lines.append(
                    f"- {r['filename']}: TRUNCATED_OR_CORRUPTED; "
                    f"production_decision={r.get('production_decision', 'REPLACEMENT_REQUIRED')}; "
                    'unchanged; no repair or inference'
                )
            if r.get('ocr_artifact'):
                summary = r.get('ocr_summary', {})
                lines.append(
                    f"- {r['filename']}: OCR coverage={r.get('ocr_coverage_pct', 0):.1f}%; "
                    f"success={r.get('ocr_success_pages', 0)}; failed={r.get('ocr_failed_pages', 0)}; "
                    f"near_empty={summary.get('empty_or_near_empty_pages', 0)}; "
                    f"confidence_mean={summary.get('confidence', {}).get('mean')}"
                )
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    return out


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--out-manifest', default='artifacts/corpus_manifest_v2.json')
    parser.add_argument('--report', default='artifacts/CORPUS_INGESTION_REPORT_v2.md')
    args = parser.parse_args()
    run_validation(args.root, out_manifest_path=args.out_manifest, report_path=args.report)
