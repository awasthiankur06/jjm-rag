# Final release readiness

**Gate: `RAG_PRODUCTION_READY`**

This release verification used the existing local disposable PostgreSQL canonical corpus and the local Qdrant collection. It did not rebuild ingestion, alter protected artifacts, re-embed content, or contact a production database.

## Results

- The resumable live PostgreSQL plus Qdrant evaluation completed all 40 cases. Routing, source identification, exact retrieval, lexical retrieval, provenance, and cross-document accuracy were each **1.00**. Recall@1/5/10 was **0.6880 / 0.9679 / 1.00**.
- The separate provenance-backed numeric acceptance suite passed **8/8** at its strict 1.00 threshold, including direct values, arithmetic, compatible units/scopes, and safe abstentions.
- The full test suite passed **114/114**. There were no failures or skips. The two warnings are third-party deprecations from Starlette and PyPDF2.
- The local Qdrant collection is present with 545 cosine, 768-dimensional points. Its prior canonical alignment audit found 545 expected candidates, zero missing/stale/mismatched/excluded points. The release health check confirmed the collection configuration and point count.
- The deployment smoke validation previously passed against a separate disposable database, including migration, ingestion, Qdrant validation, numeric lookup, calculation, policy provenance, exclusion safety, and transactional rollback. That smoke database was then destroyed; the validated canonical corpus was not changed.

## Structured sub-signal review

The historical contract's structured-only sub-signal is 0.80. Its five non-hits are intentionally not converted into guesses: each prompt omits a required district, division, state/scheme, report selection, or scope. End-to-end source/evidence validation still passes all 40 cases. The system retains evidence when available and abstains for insufficiently specified numeric requests.

## Operational release controls

Use [PRODUCTION_OPERATIONS.md](PRODUCTION_OPERATIONS.md) for environment variables, PostgreSQL backup/restore, clean canonical re-ingestion, Qdrant rebuild from PostgreSQL, health checks, rollback, and incident handling. Keep Qdrant derived from canonical PostgreSQL content; do not re-embed when canonical content IDs and text are unchanged.

The machine-readable release record is [final_release_readiness_v1.json](../artifacts/final_release_readiness_v1.json). The complete case evidence remains in [final_live_postgres_qdrant_release_validation.json](../artifacts/final_live_postgres_qdrant_release_validation.json).
