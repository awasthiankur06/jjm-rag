# Canonical Data Model

## Decision Status

- `OBSERVED`: the corpus contains HTML-exported tables, PDFs, multi-row headers, totals, geography parameters, report formats, and page-level OCR provenance.
- `DERIVED`: numeric and filtered questions require row/column preservation and deterministic computation.
- `RECOMMENDED`: retain raw source, normalized records, and source-location provenance as separate linked layers.
- `UNKNOWN`: hidden spreadsheet worksheets and authoritative revision dates are not established by this corpus.

## Layers

### 1. SourceDocument

| Field | Status | Why | Sources | Query classes |
|---|---|---|---|---|
| `document_id` | Derived | Stable internal identity without changing source | all included files | all |
| `source_filename` | Observed | Citation and audit identity | manifest, all files | exact, provenance, version |
| `source_path` | Observed | Reproducible audit location | manifest | provenance |
| `sha256` | Observed | Detects replacement and duplicate bytes | manifest/forensic artifacts | version, provenance |
| `source_status` | Derived | Separates valid, warning, blocked, excluded | validation manifest | all |
| `ingestion_status` | Derived | Prevents excluded corrupted artifacts entering production | validation manifest | provenance, safety |
| `detected_format` | Observed | Parser and citation behavior | HTML signatures, PDF signatures | all |
| `family` | Derived | Routes policy, report, template, sanction content | filename plus observed content | routing |
| `extraction_timestamp` | Derived | Reproducibility of extraction | pipeline | provenance |

### 2. ReportSnapshot

| Field | Status | Why | Sources | Query classes |
|---|---|---|---|---|
| `report_title` | Observed | Identifies report family | HTML heading/PDF title | exact, version |
| `format_code` | Observed when present | Distinguishes B11, CS1(A), F26, PM4, J6, etc. | visible report parameters | exact, filtering |
| `geography_scope` | Observed | State, all-state, district, or category scope | HTML parameter text/table rows | exact, structured |
| `reporting_date` | Observed when present | Prevents mixing snapshots | headings/parameters | version, filtering |
| `financial_year` | Observed when present | Period filter | report parameters | structured |
| `parameter_text` | Observed | Preserves filters not safely normalized | visible HTML/PDF metadata | provenance |
| `version_relationship` | Derived only after content comparison | Filename suffix is not evidence | hashes, schema, parameters, values | version |

### 3. Table and HeaderSchema

| Field | Status | Why | Sources | Query classes |
|---|---|---|---|---|
| `table_id` | Derived | Stable table citation | HTML table/PDF table | provenance |
| `header_rows` | Observed | Multi-level headers carry metric meaning | HTML exports, PDF tables | structured |
| `column_path` | Derived from header hierarchy | Avoids flattening `planned/installed/geotagged` metrics | CS1, PM4, B11, F26 | numeric, filtered |
| `row_count`, `column_count` | Observed/derived | Integrity checks | parsed tables | validation |
| `total_row_flag` | Derived | Separates aggregate from entity rows | tables with Total rows | numeric |
| `footnote_text` | Observed when present | Explains caveats and source rules | notes in HTML/PDF | policy, provenance |

### 4. GeographicEntity

| Field | Status | Why | Sources | Query classes |
|---|---|---|---|---|
| `state_or_ut` | Observed | Primary filter | state reports and parameters | exact, structured |
| `district` | Observed | District lookup/filter | B11, P1, F26, J6, PM4 | exact, structured |
| `division` | Observed | PM4 verification scope | PM4 reports | exact, structured |
| `habitation` | Observed where present | J5/C17/WQ reports | exact, structured |
| `scheme_id`, `sanction_number` | Observed only when present | Exact identifiers must not be approximated | B15, D5, WQ reports | exact |
| `normalized_name` | Derived | Case/spacing matching while retaining raw value | all tabular names | exact filtering |
| `raw_name` | Observed | Citation and lossless audit | source row | provenance |

### 5. MetricObservation

| Field | Status | Why | Sources | Query classes |
|---|---|---|---|---|
| `metric_name_raw` | Observed | Preserve source wording | all report headers | exact/provenance |
| `metric_name_normalized` | Derived | Cross-report alignment | same-schema reports | cross-document |
| `value_raw` | Observed | Audit and formatting | source cell | provenance |
| `value_numeric` | Derived only when parseable | Deterministic aggregation/comparison | numeric cells | structured |
| `unit` | Observed/derived | Distinguishes count, percent, rupees/crores | headers/notes | numeric |
| `entity_keys` | Derived links | Joins state/district/division to metric | row context | filtered/cross-document |
| `row_index`, `cell_reference` | Derived provenance | Citation to source cell | parser | provenance |

### 6. PolicySection and OCRPage

`PolicySection` retains document, page range, heading path, raw text, normalized text, and provenance. `OCRPage` retains page number, OCR text, confidence summary, rendering DPI, engine version, and warning state. These are required for Q001, Q002, Q039 and any answer sourced from either guidance PDF.

## Authority Rules

- Source cells, headers, report parameters, page text, and file hashes are `OBSERVED`.
- Name normalization, column paths, total-row flags, family labels, and numeric parsing are `DERIVED` and must retain raw values.
- Version order, latest snapshot, and semantic equivalence are `REQUIRES_VALIDATION` unless an explicit source date or authoritative metadata exists.
- The excluded `(2)` source remains `quality_state=BLOCKED`, `classification=TRUNCATED_OR_CORRUPTED`, and `ingestion_status=EXCLUDED_CORRUPTED_SOURCE`; it has no MetricObservation records.
