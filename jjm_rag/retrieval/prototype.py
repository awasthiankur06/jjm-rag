from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from PyPDF2 import PdfReader

from jjm_rag.retrieval.interfaces import Evidence, QueryRoute


EXCLUDED_FILENAME = 'Status of Pipe Water Supply in School (2).xls'
EXCLUDED_SHA256 = 'bf4eafc15390dd98688a2f0306f28457a60bc027343e5346a0bc3be2d4009ee3'
STOPWORDS = {
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'has', 'how',
    'in', 'is', 'it', 'of', 'on', 'or', 'the', 'to', 'what', 'which', 'with',
}
STATE_ALIASES = [
    'Assam', 'Maharashtra', 'Tamil Nadu', 'Uttarakhand', 'Punjab', 'Andaman & Nicobar Islands',
    'Puducherry', 'Ahmednagar', 'Karaikal', 'Pondicherry'
]


def query_constraints(query: str) -> dict[str, list[str]]:
    lower = query.lower()
    states = [state for state in STATE_ALIASES if state.lower() in lower]
    formats = []
    for token in ['PM4', 'F26', 'FUA3', 'B11', 'CS1 (A)', 'CS1(A)', 'WQ1', 'WQ2', 'J6', 'PM2', 'PM3', 'B15', 'D5']:
        if token.lower() in lower or re.sub(r'[^a-z0-9]', '', token.lower()) in re.sub(r'[^a-z0-9]', '', lower):
            formats.append(token)
    if 'pm4' in lower:
        formats.append('PM4')
    if 'f26' in lower:
        formats.append('F26')
    return {'states': states, 'formats': formats}


def format_match(text: str, token: str) -> bool:
    haystack = re.sub(r'[^a-z0-9]', '', text.lower())
    needle = re.sub(r'[^a-z0-9]', '', token.lower())
    return needle in haystack


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def normalize(value: str) -> str:
    return re.sub(r'\s+', ' ', value or '').strip()


def tokens(value: str) -> list[str]:
    return [token for token in re.findall(r'[a-z0-9]+', (value or '').lower()) if token not in STOPWORDS]


def parse_format(text: str) -> str | None:
    match = re.search(r'\bFormat\s*[-:]?\s*([A-Z0-9]+(?:\s*\([A-Za-z0-9]+\))?(?:\s*\([A-Za-z0-9]+\))?)', text, re.I)
    return normalize(match.group(1)) if match else None


def parse_metadata(text: str, heading: str | None) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        'report_title': heading or None,
        'format_code': parse_format(text),
        'state': None,
        'district': None,
        'division': None,
        'date': None,
        'financial_year': None,
        'parameter_text': text[:1200],
    }
    state_match = re.search(r'\bState\s*[:=-]\s*([^,\n]+)', text, re.I)
    if state_match:
        metadata['state'] = normalize(state_match.group(1))
    district_match = re.search(r'\bDistrict\s*[:=-]\s*([^,\n]+)', text, re.I)
    if district_match:
        metadata['district'] = normalize(district_match.group(1))
    date_match = re.search(r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b', text)
    if date_match:
        metadata['date'] = date_match.group(0)
    year_match = re.search(r'\b(?:FinYear|Financial Year|Sanction Year|Fin Year)\s*[:=-]\s*([^,]+)', text, re.I)
    if year_match:
        metadata['financial_year'] = normalize(year_match.group(1))
    return metadata


def expanded_table(table) -> list[list[dict[str, Any]]]:
    occupied: dict[tuple[int, int], dict[str, Any]] = {}
    rows = table.find_all('tr')
    max_col = 0
    for row_index, tr in enumerate(rows):
        column_index = 0
        for cell in tr.find_all(['th', 'td']):
            while (row_index, column_index) in occupied:
                column_index += 1
            rowspan = int(cell.get('rowspan') or 1)
            colspan = int(cell.get('colspan') or 1)
            value = normalize(cell.get_text(' ', strip=True))
            cell_id = f'{row_index}:{column_index}'
            origin = {
                'cell_id': cell_id,
                'value': value,
                'tag': cell.name,
                'source_row_index': row_index,
                'source_col_index': column_index,
                'rowspan': rowspan,
                'colspan': colspan,
            }
            for row_offset in range(rowspan):
                for col_offset in range(colspan):
                    occupied[(row_index + row_offset, column_index + col_offset)] = origin
                    max_col = max(max_col, column_index + col_offset + 1)
            column_index += colspan
    grid = []
    for row_index in range(len(rows)):
        grid.append([occupied.get((row_index, column_index), {'value': '', 'cell_id': None, 'source_row_index': row_index, 'source_col_index': column_index}) for column_index in range(max_col)])
    return grid


def header_paths(grid: list[list[dict[str, Any]]]) -> tuple[int, list[str]]:
    if not grid:
        return 0, []
    data_start = 0
    for index, row in enumerate(grid):
        first = normalize(row[0].get('value', '')) if row else ''
        if first.lower() == 'total' or first.isdigit():
            data_start = index
            break
    else:
        data_start = min(2, len(grid))
    header_rows = grid[:data_start]
    columns = len(grid[0]) if grid else 0
    headers = []
    for column_index in range(columns):
        values = []
        for row in header_rows:
            value = normalize(row[column_index].get('value', ''))
            if value and value not in values:
                values.append(value)
        headers.append(' > '.join(values) if values else f'column_{column_index + 1}')
    return data_start, headers


def html_document(path: Path, manifest_record: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    text = path.read_text(encoding='utf-8-sig', errors='replace')
    soup = BeautifulSoup(text, 'html.parser')
    visible = normalize(soup.get_text(' ', strip=True))
    heading_element = soup.find(id='ReportHeading')
    metadata = parse_metadata(visible, heading_element.get_text(' ', strip=True) if heading_element else None)
    document = {
        'document_id': path.stem,
        'filename': path.name,
        'sha256': manifest_record['sha256'],
        'source_path': str(path),
        'source_status': manifest_record.get('quality_state'),
        'ingestion_status': manifest_record.get('ingestion_status', 'INCLUDED'),
        'format': manifest_record.get('actual_format'),
        'family': 'report' if any(word in path.name.lower() for word in ('status', 'progress', 'coverage')) else ('template' if 'format' in path.name.lower() else 'report'),
        'metadata': metadata,
        'table_count': len(soup.find_all('table')),
    }
    rows: list[dict[str, Any]] = []
    for table_index, table in enumerate(soup.find_all('table'), start=1):
        grid = expanded_table(table)
        data_start, headers = header_paths(grid)
        document.setdefault('tables', []).append({'table_id': f'{path.stem}-table-{table_index}', 'table_index': table_index, 'headers': headers, 'row_count': len(grid), 'column_count': len(headers)})
        for row_index, row in enumerate(grid[data_start:], start=data_start):
            values = [normalize(cell.get('value', '')) for cell in row]
            if not any(values) or not values[0] or (not values[0].isdigit() and values[0].lower() not in {'total', 'subtotal', 'grand total'}):
                continue
            record = {
                'document_id': path.stem,
                'filename': path.name,
                'sha256': manifest_record['sha256'],
                'table_id': f'{path.stem}-table-{table_index}',
                'table_index': table_index,
                'row_index': row_index,
                'values': values,
                'headers': headers,
                'is_total': values[0].lower() in {'total', 'subtotal', 'grand total'},
                'metadata': metadata,
                'provenance': {'table': table_index, 'row': row_index, 'columns': list(range(len(values))), 'cell_ids': [cell.get('cell_id') for cell in row]},
            }
            rows.append(record)
    document['row_count'] = len(rows)
    document['text'] = visible
    return document, rows


def pdf_documents(path: Path, manifest_record: dict[str, Any], ocr_artifact: dict[str, Any] | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    document = {
        'document_id': path.stem,
        'filename': path.name,
        'sha256': manifest_record['sha256'],
        'source_path': str(path),
        'source_status': manifest_record.get('quality_state'),
        'ingestion_status': manifest_record.get('ingestion_status', 'INCLUDED'),
        'format': 'pdf',
        'family': 'policy' if 'guideline' in path.name.lower() else 'report',
        'metadata': {'report_title': path.stem, 'format_code': None, 'state': None, 'district': None, 'division': None, 'date': None, 'financial_year': None},
    }
    pages: list[dict[str, Any]] = []
    if ocr_artifact and path.name == 'Operational-Guidelines-JJM-2.pdf' and ocr_artifact.get('source_sha256') == manifest_record['sha256']:
        for page in ocr_artifact.get('pages', []):
            pages.append({'document_id': path.stem, 'filename': path.name, 'sha256': manifest_record['sha256'], 'page_number': page['page_number'], 'text': page['text'], 'ocr': True, 'ocr_confidence': page.get('confidence', {}).get('mean'), 'ocr_status': page.get('status'), 'metadata': document['metadata']})
    else:
        reader = PdfReader(str(path))
        for page_number, page in enumerate(reader.pages, start=1):
            pages.append({'document_id': path.stem, 'filename': path.name, 'sha256': manifest_record['sha256'], 'page_number': page_number, 'text': normalize(page.extract_text() or ''), 'ocr': False, 'ocr_confidence': None, 'ocr_status': 'not_applicable', 'metadata': document['metadata']})
    document['page_count'] = len(pages)
    document['text'] = ' '.join(page['text'] for page in pages)
    return document, pages


def build_prototype(corpus_root: str | Path, manifest_path: str | Path, output_path: str | Path, ocr_path: str | Path | None = None) -> dict[str, Any]:
    root = Path(corpus_root)
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    ocr_artifact = json.loads(Path(ocr_path).read_text(encoding='utf-8')) if ocr_path and Path(ocr_path).exists() else None
    documents: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    audit_records: list[dict[str, Any]] = []
    for record in manifest['files']:
        path = Path(record['absolute_path'])
        actual_hash = sha256_file(path) if path.exists() else None
        if (
            record['filename'] == EXCLUDED_FILENAME
            or record.get('ingestion_status') == 'EXCLUDED_CORRUPTED_SOURCE'
            or actual_hash == EXCLUDED_SHA256
        ):
            excluded.append({'filename': record['filename'], 'sha256': record['sha256'], 'reason': 'EXCLUDED_CORRUPTED_SOURCE', 'indexed': False})
            audit_records.append({
                'artifact': 'artifacts/status_pipe_water_forensic.json',
                'source_filename': record['filename'],
                'sha256': record['sha256'],
                'source_status': 'TRUNCATED_OR_CORRUPTED',
                'ingestion_status': 'EXCLUDED_CORRUPTED_SOURCE',
                'evidence': 'Audit-only exclusion record; source has no production table or row records.',
            })
            continue
        if not path.exists():
            continue
        if actual_hash != record['sha256']:
            raise ValueError(f'Corpus hash changed during prototype build: {record["filename"]}')
        if record.get('actual_format') == 'html':
            document, document_rows = html_document(path, record)
            documents.append(document)
            rows.extend(document_rows)
        elif record.get('actual_format') == 'pdf':
            document, document_pages = pdf_documents(path, record, ocr_artifact)
            documents.append(document)
            pages.extend(document_pages)
    artifact = {
        'artifact_type': 'local_read_only_retrieval_prototype_manifest',
        'corpus_manifest': str(Path(manifest_path)),
        'physical_file_count': manifest.get('physical_corpus_count', manifest.get('filesystem_count')),
        'production_usable_file_count': len(documents),
        'excluded_sources': excluded,
        'audit_records': audit_records,
        'documents': documents,
        'rows': rows,
        'pages': pages,
        'semantic_unit_count': len(pages) + len(documents),
        'production_index_policy': 'Only included documents, table rows, and PDF pages are indexed. Excluded sources produce no production records.',
    }
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding='utf-8')
    return artifact


class ExactRetriever:
    def __init__(self, artifact: dict[str, Any]):
        self.artifact = artifact
        self.audit_records = self._audit_records()

    def _audit_records(self) -> list[dict[str, Any]]:
        records = list(self.artifact.get('audit_records', []))
        if records:
            return records
        excluded = self.artifact.get('excluded_sources', [])
        manifest_path = Path(self.artifact.get('corpus_manifest', ''))
        artifact_dir = manifest_path.parent if manifest_path else Path('.')
        for audit_path in sorted(artifact_dir.glob('*forensic*.json')):
            try:
                audit = json.loads(audit_path.read_text(encoding='utf-8'))
            except (OSError, json.JSONDecodeError):
                continue
            audit_text = json.dumps(audit)
            for source in excluded:
                if source.get('sha256') and source['sha256'] in audit_text:
                    records.append({
                        'artifact': str(audit_path.relative_to(artifact_dir.parent)).replace('\\', '/'),
                        'source_filename': source['filename'],
                        'sha256': source['sha256'],
                        'source_status': source.get('reason', 'EXCLUDED_SOURCE'),
                        'ingestion_status': 'EXCLUDED_CORRUPTED_SOURCE',
                        'evidence': 'Audit-only exclusion record; source has no production table or row records.',
                    })
        return records

    def search(self, query: str, top_k: int = 10) -> list[Evidence]:
        query_tokens = set(tokens(query))
        constraints = query_constraints(query)
        results: list[Evidence] = []
        for audit in self.audit_records:
            haystack = ' '.join([audit['artifact'], audit['source_filename'], audit['sha256'], audit['source_status'], audit['ingestion_status']])
            overlap = len(query_tokens & set(tokens(haystack)))
            if overlap:
                audit_bonus = 0.4 if query_tokens & {'artifact', 'source', 'status', 'sha256', 'hash'} else 0
                results.append(Evidence(audit['artifact'], audit['artifact'], {'audit': True, 'source_filename': audit['source_filename']}, 'exact', min(1.0, overlap / max(1, len(query_tokens)) + audit_bonus), audit['evidence'], audit))
        for document in self.artifact['documents']:
            haystack = ' '.join([document['filename'], document.get('text', ''), json.dumps(document.get('metadata', {}))])
            hay_tokens = set(tokens(haystack))
            if constraints['states'] and not any(state.lower() in haystack.lower() for state in constraints['states']):
                continue
            if constraints['formats'] and not any(format_match(haystack, fmt) for fmt in constraints['formats']):
                continue
            overlap = len(query_tokens & hay_tokens)
            exact_bonus = sum(1 for token in query_tokens if token in document['filename'].lower())
            if document.get('metadata', {}).get('format_code') and document['metadata']['format_code'].lower() in query.lower():
                exact_bonus += 4
            if document.get('metadata', {}).get('report_title') and normalize(document['metadata']['report_title']).lower() in query.lower():
                exact_bonus += 4
            if overlap:
                results.append(Evidence(document['document_id'], document['filename'], {'document': document['document_id']}, 'exact', min(1.0, (overlap + exact_bonus) / max(1, len(query_tokens))), haystack[:800], document.get('metadata', {})))
        for row in self.artifact['rows']:
            haystack = ' '.join(row['values']) + ' ' + json.dumps(row['metadata'])
            if constraints['states'] and not any(state.lower() in haystack.lower() for state in constraints['states']):
                continue
            if constraints['formats'] and not any(format_match(haystack, fmt) for fmt in constraints['formats']):
                continue
            overlap = len(query_tokens & set(tokens(haystack)))
            if overlap:
                results.append(Evidence(row['document_id'] + f':row:{row["row_index"]}', row['filename'], {'table': row['table_index'], 'row': row['row_index'], 'cell_ids': row['provenance']['cell_ids']}, 'exact', min(1.0, overlap / max(1, len(query_tokens))), ' | '.join(row['values']), row['metadata']))
        results.sort(key=lambda item: (-item.relevance, item.filename, str(item.location)))
        return results[:top_k]


class StructuredRetriever:
    def __init__(self, artifact: dict[str, Any]):
        self.artifact = artifact

    def search(self, query: str, filters: dict[str, str] | None = None, top_k: int = 10) -> list[Evidence]:
        query_tokens = set(tokens(query))
        filters = filters or {}
        results: list[Evidence] = []
        document_scores: dict[str, float] = {}
        for document in self.artifact['documents']:
            metadata = document.get('metadata', {})
            haystack = ' '.join([document['filename'], document.get('text', ''), json.dumps(metadata)])
            if filters.get('state') and filters['state'].lower() not in haystack.lower():
                continue
            if filters.get('states') and not any(state.lower() in haystack.lower() for state in filters['states'].split('|')):
                continue
            if filters.get('format') and not format_match(haystack, filters['format']):
                continue
            overlap = len(query_tokens & set(tokens(haystack)))
            format_bonus = 3 if metadata.get('format_code') and metadata['format_code'].lower() in query.lower() else 0
            title_tokens = set(tokens(metadata.get('report_title', '')))
            title_overlap = len(query_tokens & title_tokens)
            title_bonus = min(1.0, title_overlap / 2) if title_overlap else 0
            document_scores[document['document_id']] = min(1.0, (overlap + format_bonus + title_bonus) / max(1, len(query_tokens)))
            if document_scores[document['document_id']] > 0:
                results.append(Evidence(document['document_id'], document['filename'], {'document': document['document_id'], 'table_count': document.get('table_count')}, 'structured', min(1.0, document_scores[document['document_id']]), document.get('text', '')[:1200], metadata))
        for row in self.artifact['rows']:
            metadata = row['metadata']
            haystack = ' '.join(row['values']) + ' ' + row['filename'] + ' ' + json.dumps(metadata)
            if filters.get('state') and filters['state'].lower() not in haystack.lower():
                continue
            if filters.get('states') and not any(state.lower() in haystack.lower() for state in filters['states'].split('|')):
                continue
            if filters.get('district') and filters['district'].lower() not in haystack.lower():
                continue
            if filters.get('format') and not format_match(haystack, filters['format']):
                continue
            overlap = len(query_tokens & set(tokens(haystack)))
            metric_overlap = len(query_tokens & set(tokens(' '.join(row['headers']))))
            row_score = min(1.0, (overlap + metric_overlap * 2) / max(1, len(query_tokens) + 2))
            score = document_scores.get(row['document_id'], 0) * 0.8 + row_score * 0.2
            if score > 0:
                results.append(Evidence(row['document_id'] + f':row:{row["row_index"]}', row['filename'], {'table': row['table_index'], 'row': row['row_index'], 'column_path': row['headers'], 'cell_ids': row['provenance']['cell_ids']}, 'structured', min(1.0, score), ' | '.join(row['values']), {'row': row, **metadata}))
        results.sort(key=lambda item: (-item.relevance, item.filename, str(item.location.get('row'))))
        diversified = []
        seen_files = set()
        selected_ids = set()
        for item in results:
            if item.filename not in seen_files:
                diversified.append(item)
                seen_files.add(item.filename)
            selected_ids.add(id(item))
        diversified.extend(item for item in results if id(item) not in selected_ids)
        return diversified[:top_k]

    def rows(self, filters: dict[str, str] | None = None) -> list[dict[str, Any]]:
        filters = filters or {}
        matched = []
        for row in self.artifact['rows']:
            haystack = ' '.join(row['values']) + ' ' + json.dumps(row['metadata'])
            if filters.get('filename') and row['filename'] != filters['filename']:
                continue
            if filters.get('state') and filters['state'].lower() not in haystack.lower():
                continue
            if filters.get('states') and not any(state.lower() in haystack.lower() for state in filters['states'].split('|')):
                continue
            if filters.get('district') and filters['district'].lower() not in haystack.lower():
                continue
            if filters.get('include_totals') != 'true' and row['is_total']:
                continue
            matched.append(row)
        return matched

    @staticmethod
    def _column_index(row: dict[str, Any], column: str | int) -> int:
        if isinstance(column, int):
            return column
        needle = normalize(column).lower()
        for index, header in enumerate(row['headers']):
            if needle in header.lower():
                return index
        raise KeyError(f'Column not found: {column}')

    @classmethod
    def numeric_value(cls, row: dict[str, Any], column: str | int) -> float:
        index = cls._column_index(row, column)
        raw = row['values'][index].replace(',', '').replace('%', '').strip()
        return float(raw)

    def aggregate(self, rows: list[dict[str, Any]], column: str | int, operation: str = 'sum') -> float:
        values = [self.numeric_value(row, column) for row in rows]
        if not values:
            raise ValueError('No numeric rows available')
        if operation == 'sum':
            return sum(values)
        if operation == 'max':
            return max(values)
        if operation == 'min':
            return min(values)
        if operation == 'mean':
            return sum(values) / len(values)
        raise ValueError(f'Unsupported aggregation: {operation}')

    def rank(self, rows: list[dict[str, Any]], column: str | int, descending: bool = True) -> list[dict[str, Any]]:
        return sorted(rows, key=lambda row: self.numeric_value(row, column), reverse=descending)


class LexicalEmbeddingProvider:
    """Replaceable local semantic proxy; intentionally does not call an external model."""

    def embed(self, text: str) -> Counter[str]:
        return Counter(tokens(text))


class SemanticRetriever:
    def __init__(self, artifact: dict[str, Any]):
        self.units: list[dict[str, Any]] = []
        for page in artifact['pages']:
            self.units.append({'source_id': page['document_id'] + f':page:{page["page_number"]}', 'filename': page['filename'], 'text': page['text'], 'location': {'page': page['page_number']}, 'metadata': {'ocr': page['ocr'], 'ocr_confidence': page['ocr_confidence'], 'ocr_status': page['ocr_status']}})
        for document in artifact['documents']:
            if document['format'] == 'html':
                self.units.append({'source_id': document['document_id'] + ':summary', 'filename': document['filename'], 'text': document.get('text', '')[:4000], 'location': {'document': document['document_id']}, 'metadata': document.get('metadata', {})})
        self.provider = LexicalEmbeddingProvider()
        self.document_frequency = Counter()
        for unit in self.units:
            self.document_frequency.update(set(self.provider.embed(unit['text'])))

    def search(self, query: str, top_k: int = 10) -> list[Evidence]:
        query_vector = self.provider.embed(query)
        results: list[Evidence] = []
        for unit in self.units:
            vector = self.provider.embed(unit['text'])
            common = set(query_vector) & set(vector)
            if not common:
                continue
            numerator = sum(query_vector[token] * vector[token] * math.log((len(self.units) + 1) / (self.document_frequency[token] + 1)) for token in common)
            q_norm = math.sqrt(sum(value * value for value in query_vector.values())) or 1
            d_norm = math.sqrt(sum(value * value for value in vector.values())) or 1
            score = numerator / (q_norm * d_norm)
            results.append(Evidence(unit['source_id'], unit['filename'], unit['location'], 'semantic', max(0.0, min(1.0, score)), unit['text'][:1200], unit['metadata']))
        results.sort(key=lambda item: (-item.relevance, item.filename, str(item.location)))
        return results[:top_k]


class DeterministicRouter:
    def route(self, query: str) -> QueryRoute:
        lower = query.lower()
        filters: dict[str, str] = {}
        entities = []
        for entity in ('Assam', 'Maharashtra', 'Tamil Nadu', 'Uttarakhand', 'Puducherry', 'Punjab', 'Andaman & Nicobar Islands', 'Ahmednagar', 'Karaikal', 'Pondicherry'):
            if entity.lower() in lower:
                entities.append(entity)
                if entity in ('Assam', 'Maharashtra', 'Tamil Nadu', 'Uttarakhand', 'Puducherry', 'Punjab', 'Andaman & Nicobar Islands'):
                    filters['state'] = entity
                elif entity in ('Ahmednagar', 'Karaikal', 'Pondicherry'):
                    filters['district'] = entity
        state_entities = [entity for entity in entities if entity in ('Assam', 'Maharashtra', 'Tamil Nadu', 'Uttarakhand', 'Puducherry', 'Punjab', 'Andaman & Nicobar Islands')]
        if len(state_entities) > 1:
            filters.pop('state', None)
            filters['states'] = '|'.join(state_entities)
        if ('which source' in lower or 'which report' in lower or 'which file' in lower) and ('and which' in lower or 'authoritative' in lower):
            return QueryRoute('CROSS_DOCUMENT', ['exact', 'structured', 'semantic', 'metadata'], filters, entities, 'The query asks for multiple source roles or evidence types.', 0.84)
        if 'artifact' in lower or 'source status' in lower or 'sha256' in lower:
            return QueryRoute('EXACT', ['exact', 'metadata'], filters, entities, 'The query requests audit identity or source status.', 0.9)
        if ('compare' in lower or 'difference' in lower) and ('with' in lower or len(entities) > 1 or 'report' in lower or 'files' in lower):
            return QueryRoute('CROSS_DOCUMENT', ['structured', 'exact', 'metadata'], filters, entities, 'The query compares multiple scopes or report families.', 0.9)
        if ('guidance' in lower or 'policy' in lower or 'operational guidance' in lower) and not ('report' in lower and 'what does' in lower):
            return QueryRoute('POLICY', ['semantic', 'exact'], filters, entities, 'Guidance and policy language routes to semantic policy retrieval.', 0.9)
        if 'report' in lower and ('what does' in lower or 'which source' in lower):
            return QueryRoute('HYBRID', ['exact', 'semantic', 'metadata'], filters, entities, 'The query combines report identity with explanatory content.', 0.82)
        if re.search(r'^(which|find|show)\b', lower) and ('report' in lower or 'file' in lower or 'field' in lower or 'source' in lower) and not re.search(r'\b(?:highest|total|count|number|value|amount)\b', lower):
            return QueryRoute('EXACT', ['exact', 'metadata'], filters, entities, 'The query requests report, field, or entity identity.', 0.87)
        if re.search(r'\b(?:what|how many|highest|total|compare|count|counts|number|value|values|amount|coverage|population|status)\b', lower):
            if 'compare' in lower or 'difference' in lower or 'which states' in lower:
                return QueryRoute('CROSS_DOCUMENT' if 'report' in lower or 'files' in lower else 'STRUCTURED', ['structured', 'metadata'], filters, entities, 'Numeric/comparison language requires deterministic structured retrieval.', 0.92)
            return QueryRoute('STRUCTURED', ['structured', 'exact', 'metadata'], filters, entities, 'Numeric, metric, total, or filter language requires structured retrieval.', 0.9)
        if any(term in lower for term in ('version', 'variant', 'duplicate', 'snapshot', 'latest')):
            return QueryRoute('VERSION', ['exact', 'metadata'], filters, entities, 'Version language requires hashes, scope, and content comparison.', 0.94)
        if any(term in lower for term in ('what does', 'how does', 'guidance', 'policy', 'define', 'definition', 'applies')):
            return QueryRoute('POLICY', ['semantic', 'exact'], filters, entities, 'Explanatory or guidance language routes to policy semantic retrieval.', 0.88)
        if any(term in lower for term in ('compare', 'which source', 'and which')):
            return QueryRoute('HYBRID', ['exact', 'structured', 'semantic', 'metadata'], filters, entities, 'The query combines multiple evidence modes.', 0.78)
        if any(term in lower for term in ('which report', 'which file', 'find', 'fields', 'format', 'sanction')):
            return QueryRoute('EXACT', ['exact', 'metadata'], filters, entities, 'Report identity, field, format, or identifier lookup favors exact retrieval.', 0.87)
        return QueryRoute('UNKNOWN', ['exact', 'semantic'], filters, entities, 'No deterministic intent signal was recognized.', 0.35, ['Query requires clarification or broader prototype routing.'])


class EvidenceFusion:
    def fuse(self, result_sets: list[list[Evidence]], top_k: int = 10) -> list[Evidence]:
        merged: dict[tuple[str, str], Evidence] = {}
        for result_set in result_sets:
            for evidence in result_set:
                key = (evidence.source_id, json.dumps(evidence.location, sort_keys=True))
                if key not in merged or evidence.relevance > merged[key].relevance:
                    merged[key] = evidence
        result = sorted(merged.values(), key=lambda item: (-item.relevance, item.filename, str(item.location)))
        return result[:top_k]


class PrototypeRetriever:
    def __init__(self, artifact: dict[str, Any]):
        self.artifact = artifact
        self.exact = ExactRetriever(artifact)
        self.structured = StructuredRetriever(artifact)
        self.semantic = SemanticRetriever(artifact)
        self.router = DeterministicRouter()
        self.fusion = EvidenceFusion()

    @staticmethod
    def _document_metadata(document: dict[str, Any]) -> dict[str, Any]:
        metadata = document.get('metadata', {})
        table_signature = [
            {
                'headers': table.get('headers', []),
                'row_count': table.get('row_count'),
                'column_count': table.get('column_count'),
            }
            for table in document.get('tables', [])
        ]
        return {
            'filename': document['filename'],
            'sha256': document.get('sha256'),
            'report_date': metadata.get('date'),
            'reporting_period': metadata.get('financial_year'),
            'source_parameters': {
                'state': metadata.get('state'),
                'district': metadata.get('district'),
                'division': metadata.get('division'),
                'format_code': metadata.get('format_code'),
            },
            'structural_signature': table_signature,
            'content_signature': document.get('sha256'),
            'ordering_evidence': 'INSUFFICIENT_VERSION_EVIDENCE',
        }

    def _version_candidates(self, query: str) -> list[Evidence]:
        constraints = query_constraints(query)
        requested_formats = {item.replace(' ', '').lower() for item in constraints['formats']}
        candidates = []
        for document in self.artifact['documents']:
            metadata = document.get('metadata', {})
            format_code = str(metadata.get('format_code') or '').replace(' ', '').lower()
            if requested_formats and format_code not in requested_formats:
                continue
            if not requested_formats and not any(term in document.get('text', '').lower() for term in ('version', 'snapshot', 'variant')):
                continue
            evidence = self._document_metadata(document)
            candidates.append(Evidence(
                document['document_id'],
                document['filename'],
                {'document': document['document_id'], 'version_evidence': evidence},
                'metadata',
                1.0,
                document.get('text', '')[:1200],
                {**metadata, 'version_evidence': evidence},
            ))
        return sorted(candidates, key=lambda item: item.filename)

    def _aligned_documents(self, query: str, states: list[str]) -> list[Evidence]:
        lower = query.lower()
        candidates = []
        for state in states:
            state_documents = []
            for document in self.artifact['documents']:
                metadata = document.get('metadata', {})
                metadata_text = json.dumps(metadata).lower()
                if state.lower() not in metadata_text:
                    continue
                haystack = f"{document['filename']} {document.get('text', '')} {metadata_text}".lower()
                identity_text = ' '.join([
                    document['filename'],
                    str(metadata.get('report_title') or ''),
                    str(metadata.get('format_code') or ''),
                    str(metadata.get('date') or ''),
                ])
                overlap = len(set(tokens(query)) & set(tokens(haystack)))
                identity_overlap = len(set(tokens(query)) & set(tokens(identity_text)))
                overlap += identity_overlap * 3
                state_documents.append((overlap, document))
            for _, document in sorted(state_documents, key=lambda item: (-item[0], item[1]['filename']))[:1]:
                metadata = document.get('metadata', {})
                alignment = self._document_metadata(document)
                alignment['entity'] = state
                alignment['report_family'] = metadata.get('format_code') or metadata.get('report_title')
                alignment['metric'] = 'document-level aligned comparison; row/column selection remains query-dependent'
                candidates.append(Evidence(
                    document['document_id'],
                    document['filename'],
                    {'document': document['document_id'], 'alignment': alignment},
                    'structured',
                    1.0,
                    document.get('text', '')[:1200],
                    {**metadata, 'alignment': alignment},
                ))
        return candidates

    def _decompose_query(self, query: str, route: QueryRoute) -> list[dict[str, Any]]:
        lower = query.lower()
        decomposition: list[dict[str, Any]] = []
        states = route.filters.get('states', '').split('|') if route.filters.get('states') else []
        if route.query_type == 'CROSS_DOCUMENT' and len(states) > 1 and 'population' in lower:
            for index, state in enumerate(states, start=1):
                structured_subquery = f'{state} rural population as on 01/04/2026'
                sub_evidence = self.structured.search(structured_subquery, {'state': state}, top_k=5)
                decomposition.append({
                    'subtask_id': f'cross-{index}',
                    'normalized_subquery': structured_subquery,
                    'query_type': 'STRUCTURED',
                    'required_evidence_type': 'structured',
                    'metadata_constraints': {'state': state},
                    'retrieval_strategy': 'structured',
                    'evidence': [item.__dict__ for item in sub_evidence],
                    'provenance': 'state-scoped structured evidence',
                    'sufficiency_status': 'pending',
                })
        if route.query_type == 'CROSS_DOCUMENT' and len(states) > 1 and 'population' not in lower:
            aligned = self._aligned_documents(query, states)
            decomposition.append({
                'subtask_id': 'cross-aligned-documents',
                'normalized_subquery': normalize(query),
                'query_type': 'CROSS_DOCUMENT',
                'required_evidence_type': 'structured',
                'metadata_constraints': {'states': states},
                'retrieval_strategy': 'structured',
                'evidence': [item.__dict__ for item in aligned],
                'provenance': 'state, report-family, date, schema, and source-hash aligned evidence',
                'sufficiency_status': 'pending',
            })
        if 'policy' in lower and 'district' in lower:
            num_q = 'district numeric value report'
            policy_q = 'policy definition and implementation guidance'
            policy_hits = [
                item for item in self.semantic.search(policy_q, top_k=10)
                if 'guideline' in item.filename.lower() or item.filename.lower().endswith('.pdf')
            ]
            numeric_hits = [
                item for item in self.exact.search(num_q, top_k=30)
                if item.filename.lower().endswith('.xls') and 'guideline' not in item.filename.lower()
            ]
            if not numeric_hits:
                numeric_hits = [
                    item for item in self.structured.search(num_q, {}, top_k=30)
                    if item.filename.lower().endswith('.xls') and 'guideline' not in item.filename.lower()
                ]
            decomposition.append({
                'subtask_id': 'hybrid-policy',
                'normalized_subquery': policy_q,
                'query_type': 'POLICY',
                'required_evidence_type': 'semantic',
                'metadata_constraints': {},
                'retrieval_strategy': 'semantic',
                'evidence': [item.__dict__ for item in policy_hits],
                'provenance': 'policy guidance evidence',
                'sufficiency_status': 'pending',
            })
            decomposition.append({
                'subtask_id': 'hybrid-numeric',
                'normalized_subquery': num_q,
                'query_type': 'STRUCTURED',
                'required_evidence_type': 'structured',
                'metadata_constraints': {'district': 'district'},
                'retrieval_strategy': 'structured',
                'evidence': [item.__dict__ for item in numeric_hits],
                'provenance': 'district numeric report evidence',
                'sufficiency_status': 'pending',
            })
        if route.query_type == 'VERSION' and 'pm4' in lower:
            version_evidence = self._version_candidates(query)
            decomposition.append({
                'subtask_id': 'version-pm4',
                'normalized_subquery': 'PM4 state snapshot comparison',
                'query_type': 'VERSION',
                'required_evidence_type': 'metadata',
                'metadata_constraints': {'report_family': 'PM4'},
                'retrieval_strategy': 'exact',
                'evidence': [item.__dict__ for item in version_evidence],
                'provenance': 'hash, filename, scope, date, parameter, schema, content, and ordering evidence',
                'sufficiency_status': 'pending',
            })
        return decomposition

    def retrieve(self, query: str, top_k: int = 10) -> dict[str, Any]:
        route = self.router.route(query)
        result_sets = []
        decomposition = self._decompose_query(query, route)
        decomposition_ids = {item['subtask_id'] for item in decomposition}
        prefer_decomposed_evidence = decomposition_ids & {'version-pm4', 'cross-aligned-documents'}
        if not prefer_decomposed_evidence:
            for strategy in route.strategies:
                if strategy == 'exact':
                    result_sets.append(self.exact.search(query, top_k))
                elif strategy == 'structured':
                    result_sets.append(self.structured.search(query, route.filters, top_k))
                elif strategy == 'semantic':
                    result_sets.append(self.semantic.search(query, top_k))
        for subtask in decomposition:
            evidence = subtask['evidence']
            if evidence:
                result_sets.append([Evidence(**item) for item in evidence])
        evidence = self.fusion.fuse(result_sets, top_k)
        evidence_payload = [item.__dict__ for item in evidence]
        sufficient = (
            route.query_type != 'UNKNOWN'
            and bool(evidence_payload)
            and max(item['relevance'] for item in evidence_payload) >= 0.15
        )
        return {'route': route.__dict__, 'evidence': evidence_payload, 'insufficient_evidence': not sufficient, 'strategies': route.strategies, 'decomposition': decomposition}
