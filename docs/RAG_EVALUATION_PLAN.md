# RAG Evaluation Plan

## Status

`RECOMMENDED` for prototype evaluation; thresholds below are initial engineering targets, not observed production results.

## Dataset

`artifacts/query_evaluation_cases.json` contains 40 corpus-grounded cases. Every case names expected source files, filters, retrieval flags, and provenance requirements. Cases cover policy, exact lookup, structured numeric, filtered analytical, cross-document, version, and provenance questions.

## Retrieval Metrics

- Recall@K for expected source/table/page evidence. Initial target: at least 0.90 on exact expected-source cases.
- Precision@K where candidate evidence is expected to be narrow. Initial target: at least 0.80 for exact and structured cases.
- Source coverage: percentage of answer claims supported by an expected source. Initial target: 1.00 for numeric claims.
- Exact-match accuracy for entity names, format codes, sanction numbers, and hashes. Initial target: 1.00 on deterministic identifiers.
- Metadata-filter accuracy for state, district, date, format, and report scope. Initial target: 1.00 on cases with explicit filters.

## Structured Answers

- Numerical correctness: computed value matches source cells and units.
- Aggregation correctness: totals/rankings use the intended population and exclude total rows when requested.
- Filtering correctness: no rows outside state/district/date/report constraints.
- Cross-document consistency: aligned metrics use compatible schemas, scopes, and periods; otherwise the answer reports incompatibility.
- Exclusion safety: excluded sources produce zero production candidates.

Initial target: zero silent numeric or filter errors in the deterministic test set.

## Generation

- Groundedness: every factual claim maps to an evidence item.
- Citation correctness: cited source, page/table/row/column and value match the answer.
- Completeness: all requested entities/metrics are addressed or explicitly marked unavailable.
- Unsupported-claim rate: initial target zero for evaluation cases.
- Insufficient-evidence behavior: ambiguous, missing-period, conflict, and excluded-source cases must abstain or qualify.

## Operational

- Latency: measure separately for exact, structured, semantic, and cross-document paths; do not set a single target before a prototype baseline.
- Failure handling: malformed source, missing metadata, OCR warnings, unavailable retrieval backend, and conflicting snapshots must produce explicit statuses.
- Observability: log query class, filters, selected sources, evidence IDs, computation steps, latency, and final citations without secrets.
- Reproducibility: pin corpus manifest/hash, parser version, query case ID, and model/configuration.

## Test Protocol

1. Run deterministic source/row/column tests.
2. Run retrieval recall and precision against expected evidence IDs.
3. Run structured answer tests with known values derived from source rows.
4. Run policy citation and abstention tests.
5. Run cross-document and version-conflict tests.
6. Run excluded-source safety tests.
7. Record residual unknowns rather than tuning thresholds to pass.
