# PostgreSQL + pgvector Benchmark

## Result

`REQUIRES_BENCHMARK`

This was specified as an isolated local benchmark. It did not run because the environment has no PostgreSQL server/client, `psycopg`, or pgvector driver installed. No corpus data was uploaded to an external service.

## Planned representative workload

The benchmark subset is based on actual JJM canonicalized evidence and includes policy/PDF semantic units, OCR pages, report descriptions, and provenance metadata. It must test:

- vector insertion and index build;
- nearest-neighbor search;
- state, district, report-family, and date filters;
- combined vector plus metadata queries;
- provenance retrieval;
- exact lookup coexistence;
- structured SQL coexistence.

Required measurements are insertion throughput, p50/p95/p99 latency where sample size permits, filtered correctness, top-k quality, index build time, and storage footprint. Results must be labeled `OBSERVED_AT_CURRENT_CORPUS_SIZE`; no scale extrapolation is valid from this small corpus.

## Current evidence

The corpus has 44 usable documents, 3,042 structured rows, 334 PDF pages, and 378 semantic units. pgvector documentation supports exact search, HNSW, IVFFlat, filtering, hybrid PostgreSQL FTS, and PostgreSQL WAL/point-in-time recovery. Those are documented capabilities, not JJM benchmark results.

## Decision

PostgreSQL + pgvector remains the initial semantic-store candidate because it keeps provenance, metadata filters, structured rows, and vectors in one operational system. Sufficiency is unresolved until a local PostgreSQL benchmark measures the actual filtered workload.

A dedicated vector database remains deferred. It should be reconsidered only if the local benchmark or production traffic demonstrates unacceptable latency, capacity, filtered recall, or operational burden.
