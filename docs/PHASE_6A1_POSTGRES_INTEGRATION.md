# Phase 6A.1 PostgreSQL integration validation

## Final gate

`PHASE_6A_PARTIALLY_VALIDATED`

The real disposable PostgreSQL validation passed for the implemented foundation and repository layer. The gate remains partial because the current ingestion CLI performs manifest-level canonical persistence rather than complete parser-derived ingestion of tables, geography, reporting dimensions, and audit rows.

No embeddings, pgvector, Grok, API, chatbot, LangChain, LangGraph, or LlamaIndex work was performed.

## Environment and security

- PostgreSQL: 18.6
- Server: local Windows service, port 5432
- Database: `jjm_rag_phase6a_test`
- Database type: disposable local database
- Production database used: no
- Credentials recorded: no
- Credential-bearing DSN stored: no
- Plaintext password removed from `package.json`

The database was created only after confirming that the requested name did not exist. Validation used the existing local PostgreSQL service.

## Migration validation

The existing [db/migrations/001_initial_schema.sql](../db/migrations/001_initial_schema.sql) was applied successfully.

Observed PostgreSQL schema:

- 9 expected tables
- 22 indexes, including primary-key, unique, and access-path indexes
- 14 foreign keys
- 1 unique constraint in addition to primary-key constraints
- 37 non-null columns
- JSONB fields accepted and round-tripped
- numeric fields accepted and round-tripped
- defaults and nullable fields validated

Migration duration was 11.97 ms in this disposable run. This is an operational observation, not a performance claim.

## Repository validation

The existing repository layer was exercised against actual PostgreSQL for:

- document create, read, SHA lookup, status update, and duplicate behavior;
- version create and retrieval;
- insufficient-version-evidence preservation;
- distinct source hash representation;
- exact provenance fields;
- structured records;
- observations, including ambiguous raw values;
- canonical content and parent-child linkage.

All repository checks passed.

The smallest required PostgreSQL compatibility changes were made inside the existing abstraction: placeholder translation, PostgreSQL conflict syntax, JSONB adaptation, and row handling. No ORM or repository framework was introduced.

## Version validation

The same source identity did not create a duplicate version. A different source SHA was represented as a distinct document/version identity. Filename suffixes were not interpreted as chronology. `INSUFFICIENT_VERSION_EVIDENCE` survived the round trip.

## Provenance validation

Representative provenance passed for:

- HTML-exported XLS data: sheet, table, section, row, column, cell, and origin-cell fields;
- PDF data: page, table, section, row, and column;
- OCR-derived PDF data: page, section, and OCR origin identifier.

No tested provenance fields disappeared in PostgreSQL.

## Numeric safety

The raw percentage value `98.50%` remained unchanged. Its normalized PostgreSQL `NUMERIC` value remained numerically equivalent to `98.50`. An ambiguous value `----` remained raw and was not silently converted. No business aggregation occurred during ingestion.

## Transaction and failure behavior

A controlled transaction inserted a valid document, then intentionally violated a foreign key. The transaction was rolled back, and the valid document was absent afterward. Result: `PASS`.

## Excluded source safety

`Status of Pipe Water Supply in School (2).xls` remained present in the physical manifest but was not persisted as a production document, structured record, observation, canonical content unit, or index entry.

The source was not repaired or ingested.

## Full-corpus run

The existing manifest-driven CLI processed:

- 45 physical sources discovered
- 44 eligible sources
- 1 excluded source
- 44 first-run logical documents
- 44 versions
- 44 structured records
- 44 observations
- 44 canonical content units
- 44 provenance rows
- 0 failures

The second run produced:

- 44 already-ingested sources
- 0 newly ingested sources
- unchanged counts for every logical entity

First-run counts and second-run counts were equal. The first and second runs took 577.24 ms and 294.29 ms respectively; these are basic operational observations only.

Important limitation: the current CLI's full-corpus behavior is manifest-level canonical persistence. It does not yet parse each source into its complete table/geography/reporting model. Accordingly, `geography_dimensions`, `reporting_dimensions`, and `ingestion_audit` remained at 0 in this run. This is why the final gate remains partial rather than a claim of complete production ingestion.

## Tests

Full suite:

```text
python -m pytest -q
27 passed, 1 warning
```

The warning is the existing PyPDF2 deprecation warning.

## Preservation audit

All protected Phase 5 artifacts remained unchanged. Final SHA-256 values:

- `artifacts/phase5_baseline_identity.json`: `b26db5198ca6415ecc1c4b7dd16654836c16a2c0ec27ef57e9bd5a8d002f3ddb`
- `artifacts/retrieval_evaluation_post_remediation.json`: `1be406020e988b51b0613303d6d6f8fcd68ebd60eec31c0c61f3f0750e2857bf`
- `artifacts/post_remediation_regression.json`: `eb7d8d23e6a2e77b8eb43fc269897422c037cb72c203fedfb7ac07d278a8560f`
- `artifacts/query_evaluation_cases.json`: `eea71106189192336e11749209b27beb827fe9e723f7a737ad963472d1695dd9`
- `artifacts/corpus_manifest_final.json`: `7970cf0a31d6b1fad97c2116e008290f926f40ba851d4872d6c900c98b502a59`

Corpus verification passed: 45 physical files, 44 production-usable, 1 excluded, and zero manifest hash mismatches. Retrieval remained 40/40 with Recall@10 1.0, cross-document accuracy 1.0, provenance accuracy 1.0, and zero regressions.

## Files changed for this validation

- [jjm_rag/persistence/database.py](../jjm_rag/persistence/database.py)
- [jjm_rag/persistence/repositories/documents.py](../jjm_rag/persistence/repositories/documents.py)
- [jjm_rag/ingestion/cli.py](../jjm_rag/ingestion/cli.py)
- [package.json](../package.json), removing the accidentally stored plaintext password
- [artifacts/phase6a1_postgres_integration.json](../artifacts/phase6a1_postgres_integration.json)

The temporary harness was used only for validation and is not part of the production design.

## Remaining limitations

- Complete parser-derived full-corpus ingestion remains pending.
- Geography and reporting dimensions are not populated by the current CLI.
- Ingestion audit rows are not populated by the current CLI.
- No formal performance benchmark was performed.
