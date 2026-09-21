# Phase 7.2K-R1 bounded candidate forensic diagnosis

## Status

`BOUNDED_VALIDATION_ONLY`

Only Q001-Q003 were processed. The runner is resumable and writes a checkpoint after every case. No production retrieval code, benchmark, corpus, PostgreSQL data, or Qdrant data was changed.

## Execution budget

Per case:

- Gemini query calls: 1
- Qdrant searches: 1
- PostgreSQL operations: 3
- document embeddings: 0
- Qdrant writes: 0

## Candidate observations

All four production channels returned bounded candidate sets of 10 for each case: exact, structured, lexical, and semantic.

### Q001

- Expected: both operational-guideline PDFs.
- Semantic Qdrant candidates contained both expected sources.
- PostgreSQL exact/lexical candidates were dominated by unrelated rural-population/content rows.
- Earliest diagnostic loss: `POSTGRES_EXACT_OR_LEXICAL`.
- Fusion retained expected guideline sources in the bounded candidate output.

### Q002

- Expected: both operational-guideline PDFs.
- Semantic Qdrant candidates contained both expected sources.
- PostgreSQL exact/lexical candidates again returned unrelated population/report rows.
- Earliest diagnostic loss: `POSTGRES_EXACT_OR_LEXICAL`.
- Fusion retained expected guideline sources in the bounded candidate output.

### Q003

- Expected: `CS1 A. Coverage.xls`.
- Semantic expected source was absent from the 25-point collection, classified as `SEMANTIC_ABSENT_FROM_25`.
- Production exact/structured/lexical candidates included the expected source in the complete candidate capture, but it was not the semantic Qdrant source.
- The case is not evidence of a Gemini failure; the expected content was outside the controlled semantic subset.

## Normalization and fusion

The current candidate objects preserve canonical content IDs for semantic/content candidates and structured record IDs for structured candidates. Provenance IDs are present where the production source supplies them. This R1 run captured the current objects and did not alter normalization or fusion.

No alternative scores or rankings were calculated. No fusion tuning was performed.

## Resume readiness

The bounded runner is ready to resume with Q004-Q015 using its checkpoint. Q001-Q003 are persisted and will be skipped by `--resume`.

## Integrity

- Qdrant Gemini collection remains at 25 logical points.
- Excluded-source points remain 0.
- Qdrant writes: 0.
- Document embeddings: 0.
- Protected artifacts and corpus hashes unchanged.
- No secrets exposed.
- Full suite remains the existing project baseline pending final post-run validation.
