# Phase 6A production foundation

## Purpose

This phase establishes the first production-oriented foundation while preserving the already validated retrieval prototype and all benchmark ground truth. It does not select an embedding model, does not build a vector database, and it does not replace the deterministic retrieval architecture.

## Non-negotiable constraints

- no chatbot/UI
- no FastAPI API yet
- no Grok generation yet
- no production embedding model selection
- no hard-coded BGE-M3 or multilingual-e5-large
- no pgvector requirement in the canonical schema
- no LangChain/LangGraph/LlamaIndex core dependency
- no modification of retrieval benchmark artifacts or source corpus
- no inclusion of the excluded corrupted source in production records

## Baseline preservation

The pre-implementation baseline remained intact. The repo validated the following before implementation:

- physical corpus files = 45
- production-usable corpus = 44
- excluded corrupted source remains excluded
- excluded source is not indexed
- retrieval remains 40/40
- Recall@10 = 1.0
- cross-document accuracy = 1.0
- provenance accuracy = 1.0
- zero regressions
- pytest baseline remained green

## Schema overview

The canonical schema is defined in [db/migrations/001_initial_schema.sql](../db/migrations/001_initial_schema.sql). It contains:

- `documents`
- `document_versions`
- `provenance_records`
- `geography_dimensions`
- `reporting_dimensions`
- `structured_records`
- `observations`
- `canonical_content`
- `ingestion_audit`

This schema is intentionally PostgreSQL-compatible while keeping the application layer abstracted from database-specific details.

## Repository layer

The persistence layer is in [jjm_rag/persistence](../jjm_rag/persistence). It defines:

- `DatabaseConfig`
- `get_database_session()`
- repository interfaces for documents, versions, provenance, structured records, observations, and canonical content

This keeps persistence concerns separated from ingestion and normalization logic.

## Provenance design

Provenance is modeled as a first-class entity. Each record can link back to:

- document
- page
- sheet
- table
- section
- row
- column
- cell
- source row/column location
- origin cell ID when available

The design avoids inventing version ordering where evidence is insufficient and uses `INSUFFICIENT_VERSION_EVIDENCE` when necessary.

## Ingestion lifecycle

The production-oriented pipeline is intentionally simple and deterministic:

1. discover source files
2. classify eligible vs excluded files
3. validate manifest eligibility
4. preserve SHA-256 identity
5. normalize metadata and provenance
6. persist canonical documents and content units
7. record ingestion audit state

The pipeline never attempts to repair malformed source content.

## Idempotency strategy

Logical idempotency is enforced via stable identities:

- source SHA-256
- document ID
- version ID
- provenance ID
- deterministic record IDs

The schema uses `INSERT OR REPLACE` and document-level uniqueness checks so running the same ingestion again does not create duplicate logical records.

## Excluded-source handling

The known corrupted source remains excluded by design:

- `Status of Pipe Water Supply in School (2).xls`
- quality state = `BLOCKED`
- production decision = `EXCLUDED_CORRUPTED_SOURCE`
- not persisted as production canonical content
- not indexed for future semantic retrieval

## CLI

The ingestion CLI exists at [jjm_rag/ingestion/cli.py](../jjm_rag/ingestion/cli.py). It supports:

- `--dry-run`
- `--validation-only`
- `--summary`
- `--manifest`

Example:

```bash
python -m jjm_rag.ingestion.cli --manifest artifacts/corpus_manifest_final.json --dry-run
```

## Database configuration

The code reads environment variables such as:

- `JJM_DATABASE_URL`
- `JJM_SQLITE_PATH`

No credentials are committed. PostgreSQL is not required for the code to run; when unavailable, the code keeps the design valid without fabricating integration success.

## Test strategy

The following are covered in the first Phase 6A test pass:

- schema existence
- excluded-source safety
- dry-run summary behavior

PostgreSQL integration tests remain explicitly pending if a disposable local PostgreSQL instance is not available.

## Known limitations

- no actual PostgreSQL integration executed yet
- no full corpus ingestion into a live PostgreSQL instance was executed
- no embedding provider implementation
- no vector/index abstraction with real provider backend yet
- no web API or UI

## Deliberately deferred decisions

- final embedding vendor selection
- semantic index implementation
- production database provisioning
- vector database adoption
- end-user application layer

## Gate status

The Phase 6A foundation is implemented as a code and schema foundation. PostgreSQL execution remains environmental and therefore not claimed as success. This is a partial foundation implementation rather than a full database-backed production claim.
