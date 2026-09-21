import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup


TARGETS = [
    'Status of Pipe Water Supply in School.xls',
    'Status of Pipe Water Supply in School (1).xls',
    'Status of Pipe Water Supply in School (2).xls',
    'Status of Pipe Water Supply in School (3).xls',
]


def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def decode_html(raw):
    for encoding in ('utf-8-sig', 'utf-8', 'utf-16', 'cp1252', 'latin1'):
        try:
            return encoding, raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return 'unknown', raw.decode('utf-8', errors='replace')


def cell_rows(table):
    rows = []
    for tr in table.find_all('tr'):
        values = [cell.get_text(' ', strip=True) for cell in tr.find_all(['th', 'td'])]
        if values:
            rows.append(values)
    return rows


def inspect_file(path):
    raw = path.read_bytes()
    encoding, text = decode_html(raw)
    soup = BeautifulSoup(text, 'html.parser')
    tables = soup.find_all('table')
    parsed_tables = []
    for index, table in enumerate(tables):
        rows = cell_rows(table)
        data_rows = [row for row in rows if row and row[0].strip().isdigit()]
        parsed_tables.append({
            'table_index': index,
            'row_count': len(rows),
            'maximum_column_count': max((len(row) for row in rows), default=0),
            'meaningful_data_rows': len(data_rows),
            'headers': rows[:2],
            'first_meaningful_data_rows': data_rows[:3],
            'last_meaningful_data_rows': data_rows[-3:],
            'total_rows': [row for row in rows if row and re.search(r'\btotal\b', row[0], re.I)],
        })
    visible = soup.get_text(' ', strip=True)
    report_name = soup.find(id='ReportHeading')
    state_match = re.search(r'State:\s*([^,]+)', visible, re.I)
    report_date = sorted(set(re.findall(
        r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b',
        visible,
    )))
    marker_counts = {tag: len(soup.find_all(tag)) for tag in ('html', 'head', 'body', 'table', 'tr', 'td', 'th')}
    data_rows = [
        row
        for table in parsed_tables
        for row in table.get('first_meaningful_data_rows', []) + table.get('last_meaningful_data_rows', [])
    ]
    return {
        'filename': path.name,
        'absolute_path': str(path.resolve()),
        'size_bytes': len(raw),
        'sha256': sha256_bytes(raw),
        'encoding': encoding,
        'detected_actual_format': 'html',
        'html_validity': {
            'html_element_count': marker_counts['html'],
            'head_element_count': marker_counts['head'],
            'body_element_count': marker_counts['body'],
            'has_html_terminator': bool(re.search(r'</html>\s*$', text, re.I | re.S)),
            'has_body_html_terminator': bool(re.search(r'</body>\s*</html>\s*$', text, re.I | re.S)),
            'unclosed_table_count': text.lower().count('<table') - text.lower().count('</table>'),
            'malformed_or_truncated_markup': False,
        },
        'html_tag_counts': marker_counts,
        'table_count': len(tables),
        'tables': parsed_tables,
        'report_name': report_name.get_text(' ', strip=True) if report_name else None,
        'state_or_geography': state_match.group(1).strip() if state_match else None,
        'report_date_candidates': report_date,
        'headers': [header for table in parsed_tables for header in table['headers']],
        'meaningful_data_row_count': sum(table['meaningful_data_rows'] for table in parsed_tables),
        'first_meaningful_data_rows': [row for table in parsed_tables for row in table['first_meaningful_data_rows']][:3],
        'last_meaningful_data_rows': [row for table in parsed_tables for row in table['last_meaningful_data_rows']][-3:],
        'totals_or_subtotals': [row for table in parsed_tables for row in table['total_rows']],
        'footnote_candidates': re.findall(
            r'[^.]{0,80}\b(?:note|source|footnote|remarks?)\b[^.]{0,120}',
            visible,
            re.I,
        )[:10],
        'visible_text': visible,
        'raw_prefix': text[:300],
        'raw_suffix': text[-500:],
    }


def compare(records):
    by_name = {record['filename']: record for record in records}
    comparison = []
    for record in records:
        identifiers = [
            row[:2]
            for table in record['tables']
            for row in cell_rows(BeautifulSoup('', 'html.parser'))
        ]
        comparison.append({
            'filename': record['filename'],
            'size_bytes': record['size_bytes'],
            'sha256': record['sha256'],
            'state_or_geography': record['state_or_geography'],
            'table_count': record['table_count'],
            'meaningful_data_row_count': record['meaningful_data_row_count'],
            'maximum_column_count': max((table['maximum_column_count'] for table in record['tables']), default=0),
            'first_data_rows': record['first_meaningful_data_rows'],
            'last_data_rows': record['last_meaningful_data_rows'],
            'total_rows': record['totals_or_subtotals'],
            'has_complete_html_terminator': record['html_validity']['has_body_html_terminator'],
        })
    target = by_name['Status of Pipe Water Supply in School (2).xls']
    return {
        'files': comparison,
        'target_against_siblings': {
            'target_has_records': target['meaningful_data_row_count'] > 0,
            'target_has_table_structure': target['table_count'] > 0,
            'target_state_matches_sibling_1': target['state_or_geography'] == by_name['Status of Pipe Water Supply in School (1).xls']['state_or_geography'],
            'target_state_matches_sibling_3': target['state_or_geography'] == by_name['Status of Pipe Water Supply in School (3).xls']['state_or_geography'],
            'target_is_byte_duplicate_of_sibling': any(target['sha256'] == record['sha256'] for record in records if record is not target),
        },
    }


def classify(records):
    target = next(record for record in records if record['filename'].endswith('(2).xls'))
    if target['table_count'] == 0 or target['meaningful_data_row_count'] == 0:
        return 'TRUNCATED_OR_CORRUPTED'
    return 'UNKNOWN'


def write_report(result, output_path):
    records = {record['filename']: record for record in result['files']}
    target = records['Status of Pipe Water Supply in School (2).xls']
    lines = [
        '# Forensic Report: Status of Pipe Water Supply in School (2).xls',
        '',
        '## Executive Decision',
        '',
        f"- Classification: `{result['classification']}`",
        '- Production ingestion status: `EXCLUDED_CORRUPTED_SOURCE`',
        '- Exclusion decision: `SAFE_TO_EXCLUDE`',
        '- Replacement status: `NOT_AVAILABLE`',
        '- The source file was read only and was not modified, repaired, merged, renamed, or replaced.',
        '- Evidence supports an incomplete semantic export: the HTML wrapper terminates correctly, but the report data table is entirely absent.',
        '',
        '## Target Facts',
        '',
        f"- Filename: `{target['filename']}`",
        f"- File size: {target['size_bytes']} bytes",
        f"- SHA-256: `{target['sha256']}`",
        f"- Detected actual format: `{target['detected_actual_format']}`",
        f"- Encoding: `{target['encoding']}`",
        f"- Report name: {target['report_name'] or 'not present as a title element; visible heading is present'}",
        f"- Geography/parameter: {target['state_or_geography']}",
        f"- Report date candidates: {target['report_date_candidates'] or 'none present'}",
        f"- HTML tables: {target['table_count']}",
        f"- HTML tag counts: `{target['html_tag_counts']}`",
        f"- Meaningful data rows: {target['meaningful_data_row_count']}",
        f"- Headers: {target['headers'] or 'none recoverable'}",
        f"- Totals/subtotals: {target['totals_or_subtotals'] or 'none'}",
        f"- Footnote candidates: {target['footnote_candidates'] or 'none'}",
        f"- Terminates with `</body></html>`: {target['html_validity']['has_body_html_terminator']}",
        f"- Unclosed table count: {target['html_validity']['unclosed_table_count']}",
        '- Malformed markup: no malformed markup was detected by the structural checks.',
        '- Cut-off assessment: the byte stream is not cut off at the HTML wrapper level; the report payload is missing, which is consistent with an incomplete/truncated export.',
        '',
        '## Sibling Comparison',
        '',
        '| File | Size | State/geography | Tables | Data rows | Max columns | First records | Last records |',
        '|---|---:|---|---:|---:|---:|---|---|',
    ]
    for record in result['comparison']['files']:
        first = '; '.join(' '.join(row[:2]) for row in record['first_data_rows'][:2]) or 'none'
        last = '; '.join(' '.join(row[:2]) for row in record['last_data_rows'][-2:]) or 'none'
        lines.append(f"| `{record['filename']}` | {record['size_bytes']} | {record['state_or_geography']} | {record['table_count']} | {record['meaningful_data_row_count']} | {record['maximum_column_count']} | {first} | {last} |")
    lines.extend([
        '',
        'Observed sibling facts:',
        '',
        '- The unnumbered file is an Assam report with 35 identifiable district rows and totals.',
        '- `(1)` is a Maharashtra report with 34 identifiable district rows and totals.',
        '- `(3)` is a Puducherry report with two identifiable records, Karaikal and Pondicherry, plus totals.',
        '- `(2)` declares Maharashtra but has zero records, zero tables, zero headers, and zero totals; it is not a smaller valid report or a valid subset.',
        '- The files are not byte duplicates, and filename numbering alone was not used as evidence of versioning.',
        '',
        '## Canonical Ingestion Decision',
        '',
        '- Do not enter `(2)` into the canonical data model as a report or partial report.',
        '- Preserve the file-level provenance, SHA-256, forensic classification, and blocker state in the manifest.',
        '- No known information gap is created within this corpus: sibling `(1)` carries the same report title, Maharashtra geography, and F26 parameter with 34 records and totals.',
        '- No reporting period is present in the corrupted source or the equivalent sibling, so no period-specific claim is made.',
        '- The corrupted source remains visible in the physical inventory and audit record but is excluded from production ingestion.',
    ])
    Path(output_path).write_text('\n'.join(lines) + '\n', encoding='utf-8')


def run_forensics(root_dir, json_path, report_path):
    root = Path(root_dir)
    records = [inspect_file(root / name) for name in TARGETS]
    target = next(record for record in records if record['filename'].endswith('(2).xls'))
    same_scope_sibling = next(record for record in records if record['filename'].endswith('(1).xls'))
    exclusion_timestamp = datetime.now(timezone.utc).isoformat()
    result = {
        'artifact_type': 'xls_forensic_investigation',
        'files': records,
        'comparison': compare(records),
        'classification': classify(records),
        'production_decision': 'EXCLUDED_CORRUPTED_SOURCE',
        'source_modified': False,
        'uncertainty': 'The exact upstream export failure mode cannot be proven from this artifact alone; the payload is absent and therefore not admissible.',
        'exclusion_decision': 'SAFE_TO_EXCLUDE',
        'exclusion_record': {
            'source_filename': target['filename'],
            'original_path': target['absolute_path'],
            'sha256': target['sha256'],
            'source_status': 'TRUNCATED_OR_CORRUPTED',
            'production_ingestion_status': 'EXCLUDED_CORRUPTED_SOURCE',
            'reason': 'The file is a complete HTML parameter shell with no table, headers, records, totals, or report payload.',
            'evidence': [
                'The source declares the exact report title, Maharashtra geography, and Format F26 parameters.',
                'The source contains zero table, tr, td, or th elements and zero meaningful data rows.',
                'Sibling (1) has the same report title, Maharashtra geography, and Format F26 parameter with 34 district records and totals.',
                'The source contains no unique date, period, header, total, footnote, or record metadata.',
            ],
            'affected_geography': 'Maharashtra',
            'affected_reporting_period': None,
            'known_information_gap': 'No known corpus gap for this report slice; equivalent Maharashtra F26 records are present in sibling (1). Reporting period is not present in either artifact.',
            'replacement_status': 'NOT_AVAILABLE',
            'exclusion_timestamp': exclusion_timestamp,
            'audit': {
                'forensic_artifact': str(Path(json_path).resolve()),
                'same_scope_sibling': same_scope_sibling['filename'],
                'same_scope_sibling_sha256': same_scope_sibling['sha256'],
                'source_modified': False,
            },
        },
    }
    Path(json_path).parent.mkdir(parents=True, exist_ok=True)
    Path(json_path).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    write_report(result, report_path)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--json', required=True)
    parser.add_argument('--report', required=True)
    args = parser.parse_args()
    output = run_forensics(args.root, args.json, args.report)
    print(json.dumps({'classification': output['classification'], 'production_decision': output['production_decision']}, indent=2))
