# Security and Operations Requirements

## Scope

These requirements apply before production implementation. The current phase only records them; it does not deploy services or transmit corpus data to external providers.

## Secrets and external APIs

- Store `XAI_API_KEY` in an approved secret manager or protected runtime secret store.
- Never commit, print, persist, or include API keys in prompts, traces, benchmark artifacts, or error messages.
- Use short-lived credentials where supported and rotate keys.
- Restrict outbound network access to approved xAI endpoints and required package/model registries.
- Confirm whether source data, OCR text, metadata, and row values may leave the deployment boundary before enabling xAI generation.
- Record model identifier and configuration without recording secrets.

## Data protection

The corpus is government reporting material, but the presence and classification of personal or sensitive fields require confirmation. Perform a field-level review before external transmission. Apply data minimization: send only the evidence needed for the answer, not the entire corpus or unrelated rows.

Required controls:

- TLS for all network connections.
- Encryption at rest for PostgreSQL, backups, model caches, and logs.
- Least-privilege database roles for ingestion, retrieval, application, and administration.
- PostgreSQL row-level security if tenancy or geography-based access is introduced; PostgreSQL documents default-deny behavior after RLS is enabled without applicable policies.
- Separate excluded-source audit history from production retrieval tables, with read-only access.
- Preserve source hashes and ingestion statuses for auditability.

## Database and provenance

Every production evidence row should retain source filename, SHA-256, source status, report family, scope, date/period, table/page, row and column identity, raw value, normalized value, and extraction warnings. Updates should be transactional and auditable. Backups must include relational data, vector indexes/rebuild metadata, schema migrations, corpus manifest, and model/version configuration.

Test restores, not just backup creation. Maintain a rebuild path from preserved source manifests and pinned parser/model versions.

## Reliability controls

- Set bounded connection, retrieval, and xAI request timeouts.
- Use bounded retries with exponential backoff only for retryable failures.
- Add circuit breaking for external API failures.
- Apply per-user and global rate limits.
- Fail closed when provenance validation, source eligibility, structured computation, or citation validation fails.
- Return explicit `INSUFFICIENT_EVIDENCE` or `CONFLICTING_EVIDENCE` states rather than guessed answers.
- Avoid retrying non-idempotent operations without an idempotency strategy.

## Observability and audit logging

Log request ID, query class, normalized filters, selected evidence IDs, computation trace ID, model ID, latency, token counts, retry count, and final validation status. Do not log secrets or unnecessary raw sensitive content. Keep immutable audit events for source selection, exclusion decisions, generated answer validation, and configuration changes.

Monitor:

- exact/structured/semantic/cross-document route rates;
- provenance and citation rejection rate;
- insufficient/conflicting evidence rate;
- xAI timeout/error/rate-limit rate;
- input/output token cost;
- PostgreSQL query latency and connection saturation;
- pgvector recall against exact-search canaries;
- index rebuild and backup/restore health.

## Network architecture

The application should access PostgreSQL over a private network with restricted security groups. External xAI access should use an egress-controlled path, explicit DNS/TLS policy, and provider allow-listing. A deployment/security team must confirm region, data residency, proxy, retention, and vendor contract requirements.

## Recovery and reproducibility

Pin:

- corpus manifest and source hashes;
- parser and normalization versions;
- embedding model, revision, dimensions, and preprocessing;
- pgvector/PostgreSQL versions and index parameters;
- xAI model identifier and generation configuration;
- schema and migration versions;
- evaluation dataset and expected-ground-truth versions.

Maintain a deterministic rebuild and evaluation command. Preserve the excluded corrupted source's audit record; never silently delete it.

## External decisions required

- Data classification and approval for xAI transmission.
- Availability and latency SLOs.
- Retention and deletion policy for prompts, evidence, responses, and traces.
- Tenant/geography authorization model.
- Database hosting, region, backup retention, and recovery objectives.
- Monthly traffic, concurrency, and cost ceiling.
- On-call ownership and incident response.

## Gate impact

These are preconditions for production implementation. The current technology phase remains `PRODUCTION_TECHNOLOGY_SELECTION_PARTIALLY_READY` until the external security/data-transfer decisions and the controlled xAI/embedding/pgvector benchmarks are complete.
