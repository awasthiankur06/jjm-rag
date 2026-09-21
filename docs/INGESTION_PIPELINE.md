# Ingestion pipeline

## Pipeline flow

1. source discovery
2. manifest eligibility assessment
3. format detection
4. parsing
5. normalization
6. canonical validation
7. provenance attachment
8. persistence
9. ingestion audit

## Eligibility rules

The pipeline must only ingest production-usable sources. The known corrupted source remains excluded:

- `Status of Pipe Water Supply in School (2).xls`

It is preserved in the corpus but is never persisted as production content.

## Determinism

The pipeline preserves:

- original source hashes
- raw values
- normalized text units
- report metadata
- provenance links
- version evidence status

No silent repair is attempted, and no malformed records are coerced without explicit policy.

## Idempotency

The system uses stable identities to avoid duplicate logical inserts. Re-running the same ingestion should produce the same logical counts instead of duplicate records.

## Failure behavior

The pipeline preserves explicit status values such as:

- `INGESTED`
- `ALREADY_INGESTED`
- `EXCLUDED`
- `VALIDATION_FAILED`
- `PARSE_FAILED`
- `PERSISTENCE_FAILED`

These are recorded in the ingestion audit table.
