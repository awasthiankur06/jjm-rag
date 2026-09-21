# Phase 5 Results

## Final gate

`PRODUCTION_TECHNOLOGY_SELECTION_PARTIALLY_READY`

The validated retrieval prototype remains `RETRIEVAL_PROTOTYPE_VALIDATED`. This phase did not build a production RAG application, change retrieval architecture, upload corpus data, or modify source/evaluation ground truth.

## Baseline preservation

[artifacts/phase5_baseline_identity.json](../artifacts/phase5_baseline_identity.json) records the critical hashes before benchmark artifacts were created. Verification confirmed:

- 40 evaluation cases remain unchanged;
- post-remediation evaluation remains 40/40 with Recall@10 = 1.0;
- post-remediation regression matrix has no regressions;
- all corpus manifest hashes match source files;
- the excluded corrupted source remains excluded and unmodified.

## What was benchmarked

### Embeddings

A real semantic benchmark dataset was generated from JJM policy text, OCR-derived policy pages, report descriptions, format terminology, and state/district metadata. Raw numeric rows were excluded. BGE-M3 and multilingual-e5-large could not run because the selected environment lacks the required model runtime packages. Result: `BENCHMARK_INCONCLUSIVE`.

### PostgreSQL + pgvector

The isolated benchmark was not executed because PostgreSQL, `psql`, `psycopg`, and pgvector drivers are unavailable. No data was sent externally. Result: `REQUIRES_BENCHMARK`.

### Grok/xAI

The controlled generation benchmark was not executed because `XAI_API_KEY` is unavailable. No external request or corpus transfer occurred. Result: `BLOCKED_BY_MISSING_XAI_API_KEY` and `REQUIRES_BENCHMARK`.

### Frameworks

The custom Python implementation remains the measured baseline with 23 passing tests. LangChain, LangGraph, and LlamaIndex are not installed, so no runtime bake-off was claimed. Their lack of demonstrated value for the current deterministic/provenance workflow supports `CUSTOM_PREFERRED`, but a framework installation benchmark remains optional.

### Reranker

No reranker was run because no candidate package/model is installed. The existing no-reranker baseline has Recall@10 = 1.0 and hybrid retrieval accuracy = 1.0. Decision: `NOT_JUSTIFIED` initially; a top-1 quality experiment may be revisited later.

## Technology decisions

- PostgreSQL structured source of truth: `SELECTED`.
- PostgreSQL B-tree/full-text exact retrieval: `SELECTED`.
- PostgreSQL + pgvector: initial direction, `REQUIRES_BENCHMARK`.
- BGE-M3 versus multilingual-e5-large: `BENCHMARK_INCONCLUSIVE`.
- xAI Grok 4.6: preferred candidate, `REQUIRES_BENCHMARK`.
- Custom Python orchestration: `CUSTOM_PREFERRED`.
- FastAPI: `REQUIRES_EXTERNAL_DECISION`.
- Reranker: `NOT_JUSTIFIED`.
- LangChain, LangGraph, LlamaIndex: not selected.
- Dedicated vector database: deferred.

## Security and deployment blockers

Before any xAI test or production implementation, confirm data-transfer approval, source-data classification, retention, endpoint/region, secret management, timeout/retry/rate-limit policy, availability SLOs, database hosting, backup/recovery objectives, and monthly traffic/cost ceilings.

## Artifacts

- [artifacts/phase5_baseline_identity.json](../artifacts/phase5_baseline_identity.json)
- [artifacts/embedding_benchmark.json](../artifacts/embedding_benchmark.json)
- [artifacts/semantic_benchmark_dataset.json](../artifacts/semantic_benchmark_dataset.json)
- [artifacts/pgvector_benchmark.json](../artifacts/pgvector_benchmark.json)
- [artifacts/grok_generation_benchmark.json](../artifacts/grok_generation_benchmark.json)
- [artifacts/framework_benchmark.json](../artifacts/framework_benchmark.json)
- [artifacts/reranker_benchmark.json](../artifacts/reranker_benchmark.json)

## Phase 6 scope

Phase 6 should remain limited to technology-enabling experiments and contracts:

1. Run BGE-M3 versus multilingual-e5-large in an approved model environment.
2. Run PostgreSQL + pgvector locally with the representative JJM subset.
3. Run the controlled Grok benchmark after credentials and security approval.
4. Add answer-level numeric/citation ground truth.
5. Finalize traffic, SLO, retention, backup, and deployment decisions.

Do not build the end-user chatbot or production API until these gates are resolved.
