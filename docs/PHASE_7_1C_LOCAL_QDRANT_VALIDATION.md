# Phase 7.1C local Qdrant validation

## Final gate

`PHASE_7_1C_LOCAL_QDRANT_PARTIALLY_READY`

Local Qdrant validation reached the requested five-record stage successfully for document embeddings and idempotent upsert. Semantic query retrieval was stopped because the first Voyage query embedding returned HTTP 429 rate limiting.

Qdrant Cloud was not called.

## Local Qdrant

- Server: 1.18.2
- Endpoint type: local HTTP
- Collection: `jjm_rag_semantic_v1`
- Vector size: 1024
- Distance: COSINE
- Existing collections `schema_entities` and `schema_layers` were not modified.
- Required project collection was created or verified without destructive recreation.

## Five-record stage

- Approved candidates selected: 5
- Voyage document embeddings: 5
- Vector dimension: 1024
- Finite vectors: PASS
- Qdrant points written: 5
- Points read back: 5
- Deterministic point IDs: PASS
- `content_unit_id` payload: present
- Provenance payload: present
- Excluded-source points: 0

The exact same five-record upsert was then executed again. The collection remained at five logical points with zero duplicate logical IDs.

## Voyage

- Provider: Voyage AI
- Model: `voyage-4-large`
- Document input type: `document`
- Query input type: `query`
- Document embedding stage: PASS
- Query stage: HTTP 429 rate-limit failure on the first attempted query

No repeated retry loop was used after the rate-limit failure.

## Stopped stages

Because the required sequence stops after a stage failure, these were not attempted:

- Q001/Q002/Q031/Q039 semantic retrieval completion
- PostgreSQL provenance resolution for returned semantic results
- hybrid retrieval
- 25-record indexing
- 100-record indexing
- full 635-record indexing
- full idempotency
- semantic benchmark

## Excluded source

`Status of Pipe Water Supply in School (2).xls` remained excluded:

- semantic candidates: 0
- embeddings: 0
- Qdrant points: 0
- retrieval eligibility: false

## Tests and preservation

- Full pytest: 39 passed, 1 warning.
- Protected artifacts: unchanged.
- Corpus hashes: matched.
- `.env` remained ignored.
- `.env.example` remained placeholder-only.
- No credentials were printed or stored.
- No local model inference or weights were introduced.

Detailed evidence: [artifacts/phase7_1c_local_qdrant_validation.json](../artifacts/phase7_1c_local_qdrant_validation.json).
