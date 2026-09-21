# Phase 7.1 cloud semantic index

## Gate

`PHASE_7_1_CLOUD_SEMANTIC_PARTIALLY_READY`

The Voyage AI and Qdrant Cloud production path is implemented. The 635-candidate dry-run passes with zero provider calls and zero Qdrant writes. Real smoke validation reached Voyage and Grok successfully, but Qdrant collection inspection timed out or was unavailable, so staged indexing stopped before any Qdrant write.

No credentials were requested, printed, stored, or placed in artifacts.

## Provider

- Embedding provider: Voyage AI
- Model: `voyage-4-large`
- Dimension: `1024`
- Document input type: `document`
- Query input type: `query`
- Vector store: Qdrant Cloud
- Distance: cosine
- Qdrant client: 1.19.0
- Voyage SDK: intentionally not installed because the current SDK introduces prohibited LangChain transitive dependencies
- Voyage integration: direct Voyage cloud HTTP API behind `VoyageEmbeddingProvider`

Local model inference is not used. No torch, transformers, sentence-transformers, FlagEmbedding, Ollama, or model weights were added by this phase.

## Candidate validation

The existing Phase 6B manifest was used without recomputation:

- candidate count: 635
- excluded candidate count: 2,922
- excluded-source candidates: 0

The indexer refuses manifests whose declared eligible count is not exactly 635 and refuses any candidate from `Status of Pipe Water Supply in School (2).xls`.

## Indexing workflow

```text
Phase 6B candidate manifest
-> exact 635-candidate validation
-> Voyage document embeddings in configurable batches
-> finite numeric/1024-dimension validation
-> Qdrant collection compatibility check
-> deterministic UUID5 point IDs
-> Qdrant upsert
-> payload metadata and filter indexes
```

Dry-run behavior is implemented and verified:

- Voyage calls: 0
- Qdrant writes: 0
- embedded: 0
- upserted: 0
- failed: 0

Full indexing was not attempted without cloud configuration.

## Qdrant identity and payload

Qdrant point IDs are deterministic UUID5 values derived from `content_unit_id`; the original `content_unit_id` is retained in the payload. Payload includes document/version identity, filename, family, report type, geography, reporting, provenance, content hash, model, dimension, and text.

Collection creation is non-destructive. Existing collections are inspected for dimension and distance; incompatible collections fail rather than being deleted or recreated. Payload indexes target state, district, report type, financial year, reporting date, source document/version, and corpus version.

## Validation status

Executed:

- Voyage one-query smoke: PASS, `voyage-4-large`, 1024 dimensions, finite vector, 493.24 ms.
- Grok one-request smoke: PASS, `grok-4.6`, exact `READY`, 2,976.61 ms.
- Dry-run: PASS, 635 candidates, zero Voyage calls, zero Qdrant writes.

Blocked or not executed:

- malformed/dimension/NaN cloud response against a live provider
- Qdrant collection creation or inspection
- Qdrant upsert/search
- metadata filters
- 635-point count
- second-pass idempotency
- content-change reindex behavior
- Q001/Q002/Q031/Q039 cloud semantic retrieval
- provenance resolution from Qdrant to PostgreSQL

Qdrant collection inspection failed before Stage 1. Because the required sequence stops on a stage failure, the 5-record, idempotency, 25-record, 100-record, full 635-record, filter, provenance, and semantic benchmark stages were not attempted.

These are recorded as unavailable, not as successful results.

## Tests

- Phase 7.1 focused tests: 4 passed
- Full suite: 39 passed, 1 warning
- Protected artifact hashes: unchanged
- Corpus hashes: unchanged
- Candidate dry-run: PASS
- Excluded-source candidate count: 0
- Prohibited LangChain packages: absent

## Required next step

Configure the approved Voyage AI and Qdrant Cloud environment variables locally, then run the staged workflow:

```text
semantic-index --dry-run
semantic-index --limit 5
semantic-index --limit 25
semantic-index --limit 100
semantic-index
```

Only after stages A-D pass should the full 635-point cloud index be built.
