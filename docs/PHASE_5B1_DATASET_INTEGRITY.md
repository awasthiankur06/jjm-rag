# Phase 5B.1 dataset integrity audit

## Gate result

`PHASE_5B1_REQUIRES_DATASET_REVIEW`

This is not a pass-to-execution gate. The preserved benchmark dataset and runner contracts are coherent, but the semantic benchmark is materially smaller than the earlier 8-case expectation and contains candidate-level anomalies that still require human review before any benchmark execution claim is made.

## Scope

This audit covered:

- dataset provenance and case count reconciliation
- semantic candidate pool integrity
- runner contract metadata and blocked execution behavior
- protected baseline preservation checks
- evidence-backed readiness for benchmark execution

## Dataset reconciliation

The preserved evidence supports a semantic dataset with four cases, not eight:

- Q001
- Q002
- Q031
- Q039

The current artifact at [artifacts/semantic_benchmark_dataset.json](../artifacts/semantic_benchmark_dataset.json) contains exactly those four cases. No preserved artifact in the project supports an 8-case semantic benchmark as the authoritative dataset.

This means the benchmark remains in a review state rather than a fully ready state, even though the dataset itself is internally consistent with the current preserved evidence.

## Candidate audit findings

The candidate pool has 375 candidate units and 375 unique IDs. The audit identified:

- 4 empty-text pages
- 3 duplicate groups
- 0 excluded-source units
- 0 invalid provenance units
- 0 corpus hash mismatches
- raw numeric rows were not introduced into the semantic set

The empty-text pages were:

- JJM_Operational_Guidelines.pdf::page::10
- JJM_Operational_Guidelines.pdf::page::131
- Operational-Guidelines-JJM-2.pdf::page::149
- Operational-Guidelines-JJM-2.pdf::page::199

The audit also flagged possible raw numeric rows in a few workbook description strings, but the final dataset excludes such raw rows and the artifact records `raw_numeric_rows_introduced: false`.

## Runner contract audit

The benchmark runners were checked for the required execution contract:

- dataset hash capture
- environment metadata capture
- package version metadata
- explicit blocked status on missing dependencies
- no fabricated success results
- no secret leakage

The runner outputs show the intended contract behavior:

- embedding runner returns `BLOCKED_BY_MISSING_EMBEDDING_RUNTIME`
- pgvector runner blocks without a DSN
- Grok runner blocks without `XAI_API_KEY`
- reranker runner blocks when the runtime is absent
- consolidated runner records blocked benchmarks without converting them to pass results

This is acceptable gate behavior. The runner contract is not the blocker.

## Baseline preservation

The protected retrieval baseline remains valid and unchanged. The preserved identity record and post-remediation artifact still show:

- 40/40 retrieval cases preserved
- Recall@10 = 1.0
- cross-document accuracy = 1.0
- provenance accuracy = 1.0
- zero regressions
- excluded corrupted source remains excluded

This gives confidence that the benchmark audit did not alter the validated retrieval architecture or ground truth.

## Decision

The project is not ready for benchmark execution under the strict gate used here because:

1. the preserved semantic benchmark is only 4 cases, and
2. candidate anomalies remain visible and should be reviewed before claiming benchmark completeness.

This does not mean the benchmark effort failed. It means the dataset is evidence-backed but not yet mature enough for broad benchmark execution claims.

## Recommendation

Before moving to execution, do one of the following:

- confirm the 4-case semantic set is the intended benchmark corpus, or
- recover and document a larger evidence-backed semantic set if one exists in source-controlled artifacts

Only after that reconciliation should the project move from `PHASE_5B1_REQUIRES_DATASET_REVIEW` to a full ready state.
