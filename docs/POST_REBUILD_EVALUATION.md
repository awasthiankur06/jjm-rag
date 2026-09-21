# Complete post-rebuild PostgreSQL evaluation

The 40-case deterministic PostgreSQL evaluation completed in resumable five-case batches. Each case, including query, route, retrieved document IDs/titles, evidence, provenance, latency, and pass/fail reason, is stored in `artifacts/post_rebuild_postgres_evaluation.json`.

## Measured result before generic title search

- Recall@1: 0.0962
- Recall@5 / Recall@10: 0.4530
- Source identification: 0.3500
- Routing: 0.6500
- Exact retrieval: 0.1250
- Lexical retrieval: 0.3333
- Structured retrieval: 0.2000
- Provenance: 0.9750
- Cross-document: 0.2500
- Excluded-source safety: pass

Numeric aggregation accuracy is not evaluable: the current 40-case contract has no independently verified answer-level numeric ground truth.

## Generic title-search experiment

Source-derived document title search was added to exact, lexical, and structured SQL. The complete rerun increased Recall@1 to 0.1218 but did not change Recall@5/10 and reduced exact and lexical source accuracy. It is retained as correct metadata coverage, not claimed as a retrieval improvement.

## Failure decision

The dataset is not re-ingested: no new source-to-database extraction defect was proven. Remaining failures are primarily generic acquisition/routing/version/cross-document contract defects. The corrupted-source expectation in Q014 is incompatible with production exclusion and must remain audit-only.

## Deterministic repair progress

Document-level ranking repaired a generic chunk-crowding defect. The complete rerun reached Recall@10 0.9509, source identification 0.90, exact retrieval 0.9063, and lexical retrieval 0.8974. Generic version/cross-document routing increased routing accuracy to 0.80. Structured retrieval remains 0.20 and is the next required repair; no semantic layer is being used to mask it.
