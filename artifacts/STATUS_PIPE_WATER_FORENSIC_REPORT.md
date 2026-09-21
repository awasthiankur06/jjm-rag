# Forensic Report: Status of Pipe Water Supply in School (2).xls

## Executive Decision

- Classification: `TRUNCATED_OR_CORRUPTED`
- Production ingestion status: `EXCLUDED_CORRUPTED_SOURCE`
- Exclusion decision: `SAFE_TO_EXCLUDE`
- Replacement status: `NOT_AVAILABLE`
- The source file was read only and was not modified, repaired, merged, renamed, or replaced.
- Evidence supports an incomplete semantic export: the HTML wrapper terminates correctly, but the report data table is entirely absent.

## Target Facts

- Filename: `Status of Pipe Water Supply in School (2).xls`
- File size: 43332 bytes
- SHA-256: `bf4eafc15390dd98688a2f0306f28457a60bc027343e5346a0bc3be2d4009ee3`
- Detected actual format: `html`
- Encoding: `utf-8-sig`
- Report name: Status of Pipe Water Supply in School
- Geography/parameter: Maharashtra
- Report date candidates: none present
- HTML tables: 0
- HTML tag counts: `{'html': 1, 'head': 1, 'body': 1, 'table': 0, 'tr': 0, 'td': 0, 'th': 0}`
- Meaningful data rows: 0
- Headers: none recoverable
- Totals/subtotals: none
- Footnote candidates: none
- Terminates with `</body></html>`: True
- Unclosed table count: 0
- Malformed markup: no malformed markup was detected by the structural checks.
- Cut-off assessment: the byte stream is not cut off at the HTML wrapper level; the report payload is missing, which is consistent with an incomplete/truncated export.

## Sibling Comparison

| File | Size | State/geography | Tables | Data rows | Max columns | First records | Last records |
|---|---:|---|---:|---:|---:|---|---|
| `Status of Pipe Water Supply in School.xls` | 232451 | Assam | 1 | 35 | 14 | 1 Bajali; 2 BAKSA | 34 Udalguri; 35 West Karbi Anglong |
| `Status of Pipe Water Supply in School (1).xls` | 229906 | Maharashtra | 1 | 34 | 14 | 1 Ahmednagar; 2 Akola | 33 Washim; 34 Yavatmal |
| `Status of Pipe Water Supply in School (2).xls` | 43332 | Maharashtra | 0 | 0 | 0 | none | none |
| `Status of Pipe Water Supply in School (3).xls` | 63147 | Puducherry | 1 | 2 | 14 | 1 Karaikal; 2 Pondicherry | 1 Karaikal; 2 Pondicherry |

Observed sibling facts:

- The unnumbered file is an Assam report with 35 identifiable district rows and totals.
- `(1)` is a Maharashtra report with 34 identifiable district rows and totals.
- `(3)` is a Puducherry report with two identifiable records, Karaikal and Pondicherry, plus totals.
- `(2)` declares Maharashtra but has zero records, zero tables, zero headers, and zero totals; it is not a smaller valid report or a valid subset.
- The files are not byte duplicates, and filename numbering alone was not used as evidence of versioning.

## Canonical Ingestion Decision

- Do not enter `(2)` into the canonical data model as a report or partial report.
- Preserve the file-level provenance, SHA-256, forensic classification, and blocker state in the manifest.
- No known information gap is created within this corpus: sibling `(1)` carries the same report title, Maharashtra geography, and F26 parameter with 34 records and totals.
- No reporting period is present in the corrupted source or the equivalent sibling, so no period-specific claim is made.
- The corrupted source remains visible in the physical inventory and audit record but is excluded from production ingestion.
