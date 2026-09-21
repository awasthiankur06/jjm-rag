# Chunking Strategy

## Decision Status

- `OBSERVED`: HTML reports are one-table exports with multi-row headers, totals, parameters, and geographic rows. PDFs have page and section structure; the scanned PDF has page-level OCR artifacts.
- `DERIVED`: arbitrary fixed-size chunks would separate metric names from values or lose table row context.
- `RECOMMENDED`: use natural retrieval units and retain parent-child links; do not choose token sizes in Phase 2 architecture validation.

## PDFs

1. Document record for identity and hash.
2. Page record for exact citation and OCR quality.
3. Section/subsection record for policy retrieval, using headings and page ranges.
4. Paragraph-level text units within a section for semantic search.
5. Table block units for PDF tables, preserving row/column structure.

The OCR PDF must retain page text, confidence, rendering method/DPI, and suspicious-page warnings. Near-empty pages cannot be silently dropped; they remain searchable with a warning or are reported as insufficient evidence.

## HTML-exported XLS reports

1. Report snapshot: title, format code, parameter text, geography, date/financial year.
2. Table record: table identity, dimensions, header hierarchy, total/subtotal rows.
3. Table-section record: header group plus associated columns where headers span multiple rows.
4. Row record: state, district, division, habitation, scheme, or total row.
5. Metric observation: one source cell/value linked to row, column path, and source coordinates.
6. Footnote/parameter record where present.

Rows should be retrievable as structured records and optionally represented as compact text for semantic context. A row chunk without its header path is not sufficient for numeric answers.

## Templates and schema-like reports

B1, B15, C17A, D5, WQ1, WQ2 and similar format-driven reports should produce schema/header units plus populated row units. Their headers are useful even when the user asks what fields a report contains. A template-like file is not automatically empty; table presence and row content decide usability.

## Excluded source

`Status of Pipe Water Supply in School (2).xls` produces no report/table/row units. It remains an audit-only source record and must not produce chunks, embeddings, index entries, or production retrieval candidates.

## Open validation

Section detection in PDFs, table extraction in PDF pages, and reliable header hierarchy reconstruction for every HTML family require prototype tests. Token chunk size, overlap, and embedding model are deliberately deferred.
