# Phase 7.1D voyage-context-4 validation

## Final gate

`PHASE_7_1D_VOYAGE_CONTEXT_4_PARTIALLY_READY`

The centralized `.env` loader resolved `voyage-context-4` and the Voyage credential as configured. Exactly one synthetic document embedding request was attempted. It failed with the provider adapter's safe `ProviderError` before a vector dimension could be observed.

Per the controlled stop rule, no retry loop, Qdrant collection inspection, collection creation, vector upsert, five-record stage, benchmark, or hybrid retrieval was attempted.

## Configuration

- provider: Voyage AI
- model: `voyage-context-4`
- intended dimension: configured by provider contract, not claimed as observed
- Qdrant target: local `jjm_rag_semantic_voyage_context_4_v1`
- Qdrant Cloud: not called
- credentials: not printed, stored, or committed

## Smoke result

The one bounded synthetic document request failed with:

```text
ProviderError: Voyage embedding request failed
```

The current adapter intentionally sanitizes provider response details, so no HTTP status was claimed from this run. No additional request was made to avoid rate-limit hammering or accidental cost.

## Not executed

- model dimension observation
- model-specific Qdrant collection inspection/creation
- five-candidate embedding/upsert
- idempotency
- Q001/Q002/Q031/Q039 retrieval
- PostgreSQL provenance resolution
- hybrid retrieval
- 40-case regression

## Preservation and tests

- Full pytest: 39 passed, 1 warning.
- Protected artifacts unchanged.
- Corpus hashes matched.
- Excluded source remains absent from candidates and vectors.
- No local model inference or weights were introduced.
- Temporary validation runner was removed.

See [artifacts/phase7_1d_voyage_context_4_validation.json](../artifacts/phase7_1d_voyage_context_4_validation.json) for machine-readable evidence.
