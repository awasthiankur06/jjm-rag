# Source-to-database reconciliation and rebuild decision

## Decision

Retain the normalized PostgreSQL schema with an additive source-title migration, but rebuild the generated canonical corpus. The prior database stored filename-derived logical titles for 27 of 41 documents that had reliable internal source titles. This is a source-metadata defect that affects display, filtering, retrieval, and citations.

## Rebuild scope

Only the known disposable PostgreSQL canonical tables were truncated and regenerated. Original PDFs/XLS files, manifests, protected evaluation artifacts, and corruption forensic evidence were not modified.

The rebuild stores the immutable physical `filename` alongside `extracted_document_title`, `title_provenance`, and `title_confidence`. The logical `report_title` is populated only from HIGH/MEDIUM-confidence internal source titles. Low/unknown PDF title evidence remains unset rather than using a filename-derived title.

## Results

- 44 eligible sources were regenerated; the corrupted school-water XLS remains absent.
- 41 reliable titles round-tripped without a mismatch.
- 34,370 structured records and observations, 3,563 content units, and 37,933 provenance rows were generated.
- A process-timeout overlap produced three duplicate successful audit events. Logical entity identities remained deduplicated. This is an operational-audit anomaly, not a source-data duplication result.

## Embeddings

Embeddings are deferred. The observed live PostgreSQL retrieval failures are primarily deterministic source-identification, structured-query, cross-document, and version-handling problems. A semantic layer must be measured independently after those contracts are repaired; it must not conceal incorrect metadata or structured extraction.
