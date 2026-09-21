# Phase 6A.2 real parser-to-PostgreSQL ingestion

## Final gate

`PHASE_6A_PARTIALLY_VALIDATED`

The real parser-to-canonical-to-PostgreSQL flow completed successfully for all 44 eligible sources. The gate remains partial because this validates the production ingestion foundation and current parser coverage; it does not introduce or validate semantic indexing, embeddings, vector search, or an application API.

## Execution

- PostgreSQL: 18.6
- Disposable database: `jjm_rag_phase6a_test`
- Physical sources: 45
- Eligible sources: 44
- Excluded sources: 1
- First run: 44 successful, 0 failed
- Second run: 44 already ingested, 0 newly inserted
- Audit statuses: 44 `SUCCESS`, 44 `ALREADY_INGESTED`
- Credentials recorded: no

The known excluded source, `Status of Pipe Water Supply in School (2).xls`, remained physically present but was not persisted as production content.

## Implemented flow

The CLI now coordinates the existing ownership boundaries:

```text
source
-> validation and format detection
-> HTML/PDF parser
-> canonical document and section/table units
-> document/version persistence
-> structured records and observations
-> geography/reporting dimensions
-> canonical content
-> cell/row/page provenance
-> ingestion audit
-> PostgreSQL
```

HTML-exported XLS rows are materialized from the span-aware parser grid. PDF pages are persisted as page sections, and the validated OCR artifact is used for `Operational-Guidelines-JJM-2.pdf` when its source hash matches. PostgreSQL-invalid NUL characters are removed at the PDF text boundary without changing other extracted content.

## Persisted counts

| Entity | Count |
|---|---:|
| Documents | 44 |
| Document versions | 44 |
| Structured records | 34,310 |
| Observations | 34,310 |
| Canonical content units | 3,557 |
| Provenance records | 37,867 |
| Geography dimensions | 2,700 |
| Reporting dimensions | 43 |
| Ingestion audit rows | 88 |

Family distribution: policy 3, report 22, sanction 1, template 8, unknown 10.

## Provenance

Representative persisted provenance includes:

- HTML/XLS: `CS1 A. Coverage.xls`, `Table 1`, row 1, column 2, cell reference `R2C3`.
- Normal PDF: `FHTCDataTable.pdf`, page sections persisted with document identity.
- OCR PDF: `Operational-Guidelines-JJM-2.pdf`, page sections persisted from the hash-verified OCR artifact.

Structured cells now retain cell-level provenance instead of sharing only a row-level location.

## Geography and reporting sanity checks

These are diagnostics of persisted data, not quality thresholds:

- distinct states: 152
- distinct districts: 796
- numeric observations: 28,437
- percentage observations: 1,090
- date observations: 138
- observations without geography: 569
- observations without reporting period: 0

The implementation does not invent geography or reporting periods. Source values that are absent or ambiguous remain absent or raw.

## Numeric handling

Raw source values and normalized numeric values are both retained where safely parseable. Percentages are identified from source values or percentage headers. Ambiguous values remain raw and are not silently converted. No business aggregation is performed during ingestion.

## Idempotency

The second full-corpus run did not increase logical counts. Identity is provided by stable SHA/document/version/record/observation/content/provenance identifiers and the database primary/unique constraints. Audit rows are operationally additive because each execution is recorded.

## Tests

- Focused Phase 6A.2 tests: 2 passed, 1 warning.
- Full suite: 29 passed, 1 warning, 0 failed, 0 skipped.

The warning is the existing PyPDF2 deprecation warning.

## Preservation audit

Protected Phase 5 evidence and corpus files were not modified. Corpus hashes remain matched, with 45 physical files and 44 production-usable sources. Retrieval remains 40/40 with Recall@10 1.0, cross-document accuracy 1.0, provenance accuracy 1.0, and zero regressions. No embeddings, pgvector, Grok calls, APIs, or framework integrations were added.

## Security

The accidental plaintext password was removed from `package.json`. No password or credential-bearing DSN is present in the result artifact, documentation, source code, or logs. The final repository scan passed.

## Remaining limitations

- No formal performance benchmark was performed.
- Geography and reporting dimensions reflect only source-observed values.
- The workspace has no Git `HEAD`, so no repository revision is recorded.

Detailed machine-readable evidence is in [artifacts/phase6a2_ingestion_result.json](../artifacts/phase6a2_ingestion_result.json).
