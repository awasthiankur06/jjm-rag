# Production environment handoff

This is the deployment reference for the validated JJM RAG system. It describes the current implementation and the local validation environment without exposing credentials, API keys, tokens, or connection strings.

## What is authoritative

| Concern | Technology / location | Production rule |
| --- | --- | --- |
| Source of truth | PostgreSQL | Authoritative store for source identity, raw values, normalized values, structured records, canonical text, and provenance. |
| Database schema | PostgreSQL `public` schema | Created by `db/migrations/001_initial_schema.sql`. No application-specific PostgreSQL schema name is required. |
| Semantic index | Qdrant | Derived retrieval index only. Every result must resolve to identical `canonical_content` text in PostgreSQL. |
| Embeddings | Gemini embedding model, when configured | Used only to query/build the derived Qdrant index; never authoritative for facts or citations. |
| Numeric questions | Deterministic PostgreSQL structured retrieval/calculation | Preserve raw data, validate compatible scope/unit/period, otherwise abstain. |
| Narrative/policy questions | Exact + lexical PostgreSQL retrieval, optionally Qdrant | Return source-grounded evidence with provenance. |
| Corrupted source | Audit/manifest only | `Status of Pipe Water Supply in School (2).xls` must never enter production tables or Qdrant. |

SQLite remains available only for lightweight unit tests. It is not the production database backend.

## Validated local environment (reference only)

The final validation used a **local disposable** PostgreSQL database named `jjm_rag_phase6a_test`, PostgreSQL **18.6**, in schema `public`. This is a validation environment, not a production database and must not be reused as the production target.

The local Qdrant collection is `jjm_rag_semantic_gemini_embedding_001_v2_header_repair`, with 545 points, 768 dimensions, and cosine distance. Its point IDs are deterministic UUID5 values derived from canonical content IDs. Use a newly named collection for a production build and switch traffic only after validation.

## Required production configuration

Supply these values through the deployment secret/configuration system, never through committed files. An explicit deployment value takes precedence over a local `.env` file.

| Variable | Required | Purpose |
| --- | --- | --- |
| `JJM_DATABASE_URL` | Yes | PostgreSQL DSN. Use a restricted application account and a dedicated database. |
| `QDRANT_URL` | For semantic retrieval | URL of the production Qdrant instance. |
| `QDRANT_COLLECTION` | For semantic retrieval | Versioned, validated derived collection name. |
| `QDRANT_API_KEY` | Only for secured/non-local Qdrant | Qdrant credential; omit only when the deployment uses an intentionally unauthenticated local service. |
| Gemini embedding credential/configuration | Only for Qdrant build/query | Provider configuration for embedding queries. Keep outside source control. |
| `DEFAULT_CHUNK_SIZE` | No | Optional canonical chunk size override; default is `800`. |
| `DEFAULT_CHUNK_OVERLAP` | No | Optional canonical chunk overlap override; default is `120`. |

The database URL must identify a dedicated production database, for example a name chosen by the deployment team such as `jjm_rag_production`; do not place the actual URL or password in documentation or artifacts.

## PostgreSQL schema

Apply exactly this migration to an empty production database:

```text
db/migrations/001_initial_schema.sql
```

The migration uses transaction-safe DDL and creates these tables:

| Table | Purpose | Key relationships |
| --- | --- | --- |
| `documents` | One physical source per SHA-256, title/report metadata, inclusion and ingestion status | `document_id` primary key; `sha256` unique. |
| `document_versions` | Snapshot/version evidence without inferring order from filename suffixes | References `documents`. |
| `provenance_records` | Page, sheet, table, row, column, cell, and source-coordinate evidence | References `documents`. |
| `geography_dimensions` | State/district/division/block/habitation dimensions | References `documents`. |
| `reporting_dimensions` | Date, period, financial year, format and report family | References `documents`. |
| `structured_records` | Table-derived raw and numeric values, unit, header path | References document, geography, reporting, provenance. |
| `observations` | Observation-level raw/normalized values and normalization status | References document, structured record, provenance. |
| `canonical_content` | Canonical retrieval units and their source text/provenance | References document, provenance; supports `parent_content_id`. |
| `ingestion_audit` | Per-source ingestion status/failure evidence | Optionally references document. |

Primary keys are text stable IDs. Important constraints include unique document SHA-256, mandatory document/record ownership, and foreign keys from all fact/content tables to their evidence dimensions. Timestamps default to PostgreSQL `CURRENT_TIMESTAMP`. `value_raw` remains text; `value_numeric` is PostgreSQL `NUMERIC` and is populated only when safely parseable.

The migration creates indexes for document SHA-256, family, report type, format code, ingestion status, and document foreign-key access paths. The complete field-level DDL is [001_initial_schema.sql](../db/migrations/001_initial_schema.sql); the short data-model reference is [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md).

## Production deployment sequence

1. Create an empty, dedicated PostgreSQL database and least-privilege application account. Confirm the target is not an organizational or unrelated database.
2. Configure `JJM_DATABASE_URL` in the deployment secret store.
3. Apply `db/migrations/001_initial_schema.sql` once to the empty database.
4. Run `python -m jjm_rag.ingestion.cli --validation-only` first, then run `python -m jjm_rag.ingestion.cli` for the canonical ingestion.
5. Verify all 44 eligible sources are represented and the corrupted XLS is absent from `documents`, `structured_records`, `observations`, `canonical_content`, and Qdrant.
6. Run ingestion a second time without truncation. It must report existing items as already ingested and must not increase logical entity counts.
7. Build a new, versioned Qdrant collection from current `canonical_content`. Use `python -m jjm_rag.production.cloud_cli --dry-run` before a real index build; retain a checkpoint for resumability.
8. Validate Qdrant point count, 768-dimensional cosine configuration, deterministic IDs, canonical text equality, and zero excluded-source points. Only then set `QDRANT_COLLECTION` to the new collection.
9. Run `pytest -q`, the numeric acceptance suite, and the resumable PostgreSQL/Qdrant evaluation against that production-like environment.
10. Keep the previous known-good Qdrant collection until post-release health checks pass.

## Runtime retrieval contract

1. The deterministic router classifies the request and extracts filters such as geography, report family/type, date/financial year, format, and source scope.
2. Structured/numeric requests query PostgreSQL first. Calculations use explicit, provenance-backed operands and reject duplicate, mismatched-unit, mismatched-period, or mixed-scope candidates.
3. Exact and lexical PostgreSQL retrieval supply source identity and policy/narrative evidence.
4. Qdrant can add semantic candidates only after each point is verified against the current `canonical_content` ID and text.
5. The answer layer returns citations/provenance. It abstains when required entities, scope, dates, units, or evidence are missing.
6. When multiple compatible report categories could answer a numeric request, the API returns a `clarification` object with a grounded question and only source-derived choices. The browser preserves the prior question and resubmits it with the selected category; it never guesses or merges incompatible sources.

## Frontend and backend: local run instructions

There is no separate Node/React frontend service in this repository. The browser UI is the static application in `jjm_rag/production/static/`, and the FastAPI backend serves it together with the API:

| URL | Purpose |
| --- | --- |
| `http://127.0.0.1:8000/` | Browser question console (frontend). |
| `http://127.0.0.1:8000/health` | Liveness check. |
| `http://127.0.0.1:8000/ready` | Dependency/readiness check; reports semantic and generation availability. |
| `POST http://127.0.0.1:8000/api/v1/query` | Query API. Body: `{ "query": "...", "filters": {}, "options": { "retrieval_only": false } }`. |

### Windows local development

From the repository root in PowerShell:

```powershell
.venv\Scripts\python.exe -m uvicorn jjm_rag.production.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/` in a browser. Keep this terminal open while testing; use `Ctrl+C` to stop the application.

For access from other machines on a controlled private network, bind only after applying the normal firewall, reverse-proxy, TLS, authentication, and network-access controls:

```powershell
.venv\Scripts\python.exe -m uvicorn jjm_rag.production.main:app --host 0.0.0.0 --port 8000
```

Do not expose the development Uvicorn server directly to the public internet. Use a process manager and a TLS-terminating reverse proxy for a deployed service. Before starting either command, configure the required `JJM_DATABASE_URL` and optional Qdrant/provider variables through the environment as described above.

## Health checks and acceptance checks

After deployment, verify:

- PostgreSQL connectivity and all nine tables above exist in `public`.
- `documents`, `structured_records`, `observations`, `canonical_content`, and `provenance_records` contain internally consistent data.
- The excluded source has a count of zero in every production table and the Qdrant collection.
- A direct numeric lookup includes raw value, typed numeric value, source, and provenance.
- A compatible calculation exposes validated operands and result provenance.
- An unnamed state/division/district request and mixed-scope calculation abstain rather than guess.
- Qdrant point payload text and content ID match PostgreSQL canonical content.

The validated release baseline is recorded in [FINAL_RELEASE_READINESS.md](FINAL_RELEASE_READINESS.md). It achieved 40/40 completed evaluation cases, 8/8 numeric acceptance cases, and 114/114 tests.

## Backup, rollback, and re-ingestion

Back up PostgreSQL before migration or re-ingestion and test restoring it to a separate disposable database. Never truncate a production database to obtain idempotency. If ingestion fails, the transaction must roll back and the source must not be marked `INGESTED`.

For a semantic-index failure, switch `QDRANT_COLLECTION` back to the prior validated collection; do not alter canonical PostgreSQL data. For a PostgreSQL incident, restore into a separate environment, verify counts/provenance and exclusion safety, then promote only after acceptance checks pass. The detailed procedures are in [PRODUCTION_OPERATIONS.md](PRODUCTION_OPERATIONS.md).
