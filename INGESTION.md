# Ingestion and Extraction

This project intentionally implements the Phase 1 pipeline first, as approved by the architecture baseline.

## Pipeline

1. File discovery
2. File identification
3. Format detection
4. Family classification
5. Parser selection
6. Extraction
7. Extraction validation
8. Normalized representation
9. Metadata capture
10. Version and hash detection

## Important constraints

- The original source files are never modified.
- .xls files are treated as potentially HTML-exported tables, not assumed to be native spreadsheets.
- parser choice is based on observed file content and format signatures.
- all extracted content retains provenance.

## Validation

The ingestion layer emits a validation report that records:

- file count
- successful parse count
- failed file count
- parser selected per file
- format detected
- family assignment
- warnings
- extraction quality
