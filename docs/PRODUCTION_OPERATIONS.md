# Production Operations

## Configuration

Set configuration only through environment variables. Do not commit database URLs with passwords, provider keys, or tokens.

- `JJM_DATABASE_URL`: PostgreSQL connection string.
- `QDRANT_URL`, `QDRANT_COLLECTION`, `QDRANT_API_KEY`: derived semantic index configuration.
- Gemini/XAI provider variables: optional derived retrieval/generation services; deterministic PostgreSQL retrieval remains available when either is unavailable.

PostgreSQL is the canonical system of record. Qdrant contains only rebuildable semantic candidates and never becomes an authority for source values or provenance.

## Backup and restore

Before a migration or corpus rebuild, create a PostgreSQL backup using the environment-provided database connection. Store the backup outside the repository and verify it can be restored into a separate disposable database.

Restore into a new disposable database first. Apply the schema migration only when restoring schema-free data; otherwise inspect migration history and do not reapply destructive changes. Validate document, structured-record, provenance, and canonical-content counts before promoting the restored environment.

## Canonical re-ingestion

1. Preserve the protected source manifests and evaluation artifacts.
2. Confirm the target database is explicitly disposable or approved for the operation.
3. Apply migrations to an empty target.
4. Run `python -m jjm_rag.ingestion.cli` with environment-based PostgreSQL configuration.
5. Confirm 44 eligible sources are ingested and `Status of Pipe Water Supply in School (2).xls` is absent from production tables.
6. Run ingestion a second time. Existing logical documents must report `ALREADY_INGESTED`; counts must not grow.
7. Run the PostgreSQL and numeric acceptance evaluations before using the result.

Never repair or ingest the excluded corrupted workbook.

## Qdrant rebuild

1. Generate semantic candidates from current `canonical_content` using `build_candidate_manifest`.
2. Verify the candidate manifest excludes the corrupted source.
3. Use a new, versioned collection name; do not overwrite a known-good collection.
4. Embed/upsert candidates with deterministic point IDs.
5. Validate point count, 768 dimensions, deterministic IDs, canonical content IDs, canonical text equality, and zero excluded-source points.
6. Switch `QDRANT_COLLECTION` only after validation. Retain the prior collection for rollback.

## Health checks

Run these checks after deployment and before a release:

- PostgreSQL connection and migration/schema inspection.
- Documents, canonical content, structured records, observations, and provenance counts are non-zero and internally consistent.
- Excluded corrupted source count is zero in documents, structured records, canonical content, and Qdrant.
- A direct numeric fact returns raw value, numeric value, source, and provenance.
- A compatible calculation returns validated operands and a deterministic result.
- A missing-entity or mixed-scope calculation abstains.
- Qdrant points resolve to current canonical PostgreSQL text.

## Rollback and incident response

If an ingestion, migration, or index validation fails, do not mark the source as successfully ingested. Roll back the transaction, retain the audit failure, and keep the prior known-good PostgreSQL/Qdrant configuration active.

For a Qdrant issue, remove the new collection from traffic by restoring the previous `QDRANT_COLLECTION`; do not modify canonical PostgreSQL records. For a PostgreSQL issue, restore to a separate environment, validate counts and provenance, then promote only after acceptance checks pass.

Record the incident, affected source hashes, migration/index version, validation output, remediation, and final verification. Never include secrets in the incident record.
