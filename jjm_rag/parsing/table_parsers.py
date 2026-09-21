from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from bs4 import BeautifulSoup

from jjm_rag.ingestion.format_detection import detect_format
from jjm_rag.models.canonical import Document, Provenance, Section, SourceMetadata, Table


def _derive_header_paths(header_rows: list[list[dict[str, Any]]], num_cols: int) -> list[list[str]]:
    paths = [[] for _ in range(max(num_cols, 1))]
    serial_columns: set[int] = set()
    if not header_rows:
        return [[f"col_{idx + 1}"] for idx in range(num_cols)]

    for row in header_rows:
        for cell in row:
            text = str(cell.get("text") or "").strip()
            # Serial-number columns and numeric cells are not semantic headers.
            # Geographic labels such as "State/ UT" are: dropping them turns the
            # column into ``col_2`` and prevents downstream geography extraction.
            if not text or re.fullmatch(r"[\d,.]+%?", text):
                continue
            start = int(cell.get("source_col_index") or 0)
            span = int(cell.get("colspan") or 1)
            # Legacy exports often append a code legend (A, B, C, …) below
            # a rowspan ``S. No.`` header. The legend is visually shifted but
            # appears at column zero in HTML. Preserve the authoritative
            # serial classification so it can never become a numeric metric.
            if text.lower() in {"s. no.", "s no.", "s.no", "s no"}:
                serial_columns.update(range(start, min(start + span, num_cols)))
                continue
            for col_idx in range(start, min(start + span, num_cols)):
                if text not in paths[col_idx]:
                    paths[col_idx].append(text)

    for idx in range(len(paths)):
        if idx in serial_columns:
            # ``col_1`` is the established non-metric sentinel consumed by
            # canonical persistence; retaining it keeps serial values out of
            # structured records while preserving the source row content.
            paths[idx] = [f"col_{idx + 1}"]
            continue
        if not paths[idx]:
            paths[idx] = [f"col_{idx + 1}"]
    return paths


class HtmlTableParser:
    parser_name = "html_table_parser"

    def parse(self, path: Path, family: str = "unknown") -> Document:
        content = path.read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(content, "html.parser")
        tables = soup.find_all("table")
        parsed_tables: list[Table] = []
        for idx, table in enumerate(tables, start=1):
            # Build explicit grid preserving rowspan/colspan and provenance
            occupied = {}
            source_cells = []
            rows = table.find_all('tr')
            max_col = 0
            cell_id_counter = 0
            for r_idx, tr in enumerate(rows):
                c_idx = 0
                for el in tr.find_all(['th', 'td']):
                    # advance to next free column
                    while (r_idx, c_idx) in occupied:
                        c_idx += 1
                    colspan = int(el.get('colspan') or 1)
                    rowspan = int(el.get('rowspan') or 1)
                    raw_text = el.get_text(separator=' ', strip=False)
                    norm_text = el.get_text(separator=' ', strip=True)
                    cell_id = f"c{cell_id_counter}"
                    cell_id_counter += 1
                    source_cell = {
                        'cell_id': cell_id,
                        'tag': el.name,
                        'raw_text': raw_text,
                        'text': norm_text,
                        'rowspan': rowspan,
                        'colspan': colspan,
                        'source_row_index': r_idx,
                        'source_col_index': c_idx,
                    }
                    source_cells.append(source_cell)
                    for rr in range(r_idx, r_idx + rowspan):
                        for cc in range(c_idx, c_idx + colspan):
                            occupied[(rr, cc)] = {'origin_cell_id': cell_id}
                            if cc + 1 > max_col:
                                max_col = cc + 1
                    c_idx += colspan

            # construct grid mapping with full cells for every coordinate
            num_rows = len(rows)
            num_cols = max_col
            grid = []
            for r in range(num_rows):
                row_cells = []
                for c in range(num_cols):
                    entry = occupied.get((r, c))
                    if entry is None:
                        row_cells.append({'origin_cell_id': None, 'is_blank': True})
                    else:
                        # find origin cell
                        origin = next((s for s in source_cells if s['cell_id'] == entry['origin_cell_id']), None)
                        # normalized fill value: same as origin but traceable
                        fill = {
                            'origin_cell_id': entry['origin_cell_id'],
                            'tag': origin['tag'] if origin else None,
                            'text': origin['text'] if origin else None,
                            'raw_text': origin['raw_text'] if origin else None,
                            'is_span_filler': (origin is not None and (origin['rowspan'] > 1 or origin['colspan'] > 1) and not (origin['source_row_index']==r and origin['source_col_index']==c)),
                            'source_row_index': origin['source_row_index'] if origin else None,
                            'source_col_index': origin['source_col_index'] if origin else None,
                        }
                        row_cells.append(fill)
                grid.append(row_cells)

            # derive headers heuristically (first non-empty row of original source rows)
            headers = []
            header_rows: list[list[dict[str, Any]]] = []
            header_row_indexes: list[int] = []
            if source_cells:
                header_cell_rows: dict[int, list[dict[str, Any]]] = {}
                for s in source_cells:
                    if s.get('tag') == 'th':
                        header_cell_rows.setdefault(int(s['source_row_index']), []).append(s)
                # Some legacy exports use <th> in body rows. A table header is
                # only the leading contiguous block before the first data (<td>)
                # row, not every row that happens to contain a <th> element.
                cells_by_row: dict[int, list[dict[str, Any]]] = {}
                for cell in source_cells:
                    cells_by_row.setdefault(int(cell['source_row_index']), []).append(cell)
                for row_index in range(num_rows):
                    row_cells = cells_by_row.get(row_index, [])
                    if not row_cells or any(cell.get('tag') == 'td' for cell in row_cells):
                        break
                    values = [str(cell.get('text') or '').strip() for cell in row_cells]
                    nonempty_values = [value for value in values if value]
                    numeric_cells = sum(bool(re.match(r'^\s*[\d,.]+%?\s*$', value)) for value in nonempty_values)
                    # Some source exports insert a second, ordinal column
                    # legend ("1", "2", ..., "(5+6)") below the semantic
                    # headings.  Consume it so it cannot become a data row,
                    # but do not add it to header paths.
                    ordinal_legend = bool(nonempty_values) and all(
                        re.fullmatch(r'\d+|\(\d+\+\d+\)', value) for value in nonempty_values
                    )
                    if ordinal_legend:
                        header_row_indexes.append(row_index)
                        continue
                    if row_index > 0 and numeric_cells >= max(1, len(nonempty_values) // 2):
                        break
                    if any(cell.get('tag') == 'th' for cell in row_cells):
                        header_row_indexes.append(row_index)
                    else:
                        break
                header_rows = [
                    sorted(header_cell_rows[index], key=lambda x: x['source_col_index'])
                    for index in header_row_indexes
                    if index in header_cell_rows
                    and not all(
                        re.fullmatch(r'\d+|\(\d+\+\d+\)', str(cell.get('text') or '').strip())
                        for cell in header_cell_rows[index]
                        if str(cell.get('text') or '').strip()
                    )
                ]
                data_start_row = max(header_row_indexes) + 1 if header_row_indexes else 0
                # Legacy HTML sometimes carries duplicate visual header cells
                # beyond every real <td> column.  They have no source data and
                # must not create phantom numeric metrics.
                data_columns = {
                    int(cell['source_col_index'])
                    for cell in source_cells
                    if int(cell['source_row_index']) >= data_start_row
                    and cell.get('tag') == 'td'
                    and str(cell.get('text') or '').strip()
                }
                if data_columns:
                    num_cols = max(data_columns) + 1
            header_paths = _derive_header_paths(header_rows, num_cols)
            # The leaf of each source-column path is the fact metric. Flattening
            # every header cell shifts multi-row headings into data columns.
            headers = [path[-1] if path else f'col_{index + 1}' for index, path in enumerate(header_paths)]
            data_start_row = max(header_row_indexes) + 1 if header_row_indexes else 0
            rows = [
                [cell.get('text') if cell.get('text') is not None else '' for cell in row[:num_cols]]
                for row in grid[data_start_row:]
            ]

            parsed_tables.append(
                Table(
                    table_id=f"{path.stem}-table-{idx}",
                    name=f"Table {idx}",
                    headers=headers,
                    rows=rows,
                    provenance=Provenance(
                        document_id=path.stem,
                        source_path=str(path),
                        table_name=f"Table {idx}",
                    ),
                    structured={'num_rows': num_rows, 'num_cols': num_cols, 'source_cells': source_cells, 'grid': grid, 'header_paths': header_paths, 'data_start_row': data_start_row},
                    header_paths=header_paths,
                )
            )

        section = Section(
            section_id=f"{path.stem}-section-1",
            title=path.stem,
            text=soup.get_text(" ", strip=True)[:2000],
            tables=parsed_tables,
            provenance=Provenance(document_id=path.stem, source_path=str(path), section_path=path.stem),
        )

        metadata = SourceMetadata(
            source_path=str(path),
            filename=path.name,
            file_size=path.stat().st_size,
            detected_format=detect_format(path).format_name,
            parser_name=self.parser_name,
        )

        return Document(
            document_id=path.stem,
            source_path=str(path),
            source_metadata=metadata,
            family=family,
            sections=[section],
            tables=parsed_tables,
        )
