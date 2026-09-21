# Post-Remediation Retrieval Results

## Final decision

The fresh post-remediation evaluation executed all 40 cases exactly once. Runtime values matched the persisted artifact, the query and prototype-manifest hashes were recorded, all existing tests passed, and no previously passing case regressed.

Final gate:

> RETRIEVAL_PROTOTYPE_VALIDATED

This gate is based on the complete evidence set, not only on the four targeted cases. The prototype remains a local deterministic prototype; this result does not authorize production infrastructure selection.

## Artifacts and integrity

- [artifacts/pre_remediation_eval_identity.json](../artifacts/pre_remediation_eval_identity.json) preserves the pre-remediation evaluation identity.
- [artifacts/retrieval_evaluation_results.json](../artifacts/retrieval_evaluation_results.json) is the preserved pre-remediation fresh run.
- [artifacts/retrieval_evaluation_post_remediation.json](../artifacts/retrieval_evaluation_post_remediation.json) is the newly generated post-remediation run.
- [artifacts/post_remediation_regression.json](../artifacts/post_remediation_regression.json) contains the complete 40-row comparison matrix.
- [artifacts/retrieval_evaluation_baseline.json](../artifacts/retrieval_evaluation_baseline.json) was not modified.
- The excluded corrupted source was not indexed or modified.
- The source corpus and corpus manifest were not modified.

Post-run proof recorded in the new evaluation artifact:

- case_count = 40
- executed_case_count = 40
- unique case IDs = 40
- runtime_equals_persisted = true
- post-remediation artifact generated after the code changes
- post-remediation failure categories = {}

## Exact remediation

### Q014: excluded-source audit provenance

The persisted prototype manifest did not contain its optional `audit_records` list, although it did contain the excluded source and its SHA-256. The exact retriever now reconstructs audit-only records by matching excluded-source hashes against available forensic JSON artifacts. Queries that request artifact, source-status, hash, or provenance evidence receive an audit relevance bonus.

This is general because it applies to any excluded source with a matching forensic artifact and never adds the excluded source to production documents, rows, or pages. The source remains excluded exactly as required.

Result: Q014 passes source and audit evidence validation without retrieving the corrupted source as data.

### Q021 and Q040: version evidence

Version queries now expand to all documents in the requested report family and expose evidence fields for:

- candidate filename
- SHA-256
- report date
- reporting period
- source parameters and state scope
- structural signature
- content signature
- ordering evidence

The implementation explicitly records `INSUFFICIENT_VERSION_EVIDENCE` for ordering when no authoritative chronology is present. It does not infer precedence from `(1)`, `(2)`, or `(3)` filename suffixes.

The four PM4 files are therefore returned as distinct state-scoped snapshots of the same report family. Q040 correctly remains answerable only as “no” for suffix-only latest-version determination. This is a general report-family evidence rule, not a Q021/Q040 hardcode.

Result: Q021 and Q040 pass their source-evidence requirements without fabricating version ordering.

### Q036: cross-document alignment

Multi-state cross-document decomposition now selects one candidate per requested geography using shared report identity, format, date, and query terms. It attaches alignment metadata containing source hash, report family, entity/geography, date/reporting period, structural signature, and provenance.

This replaces the prior hardcoded B11 population subquery for non-population comparisons. It is reusable for state-scoped report families and does not target the J6 filenames by special case.

The corpus and evaluation cases provide source-level expected evidence but no answer-level expected values for this comparison. The evaluator therefore proves aligned source selection and provenance, while numeric row/column answer correctness remains `NOT_EVALUABLE`; no values were invented.

Result: Q036 passes the available evidence contract, with the answer-level limitation explicitly retained.

## Targeted and full tests

Targeted regression tests: 3 passed, 1 warning.

Full test suite: 23 passed, 1 warning. The warning is the existing PyPDF2 deprecation warning.

## Baseline, pre-remediation, and post-remediation metrics

| Metric | Baseline | Pre-remediation fresh | Post-remediation fresh |
|---|---:|---:|---:|
| Routing accuracy | 0.85 | 0.85 | 0.85 |
| Recall@1 | 0.44444444444444453 | 0.48717948717948717 | 0.4957264957264957 |
| Recall@3 | 0.8333333333333334 | 0.8141025641025641 | 0.8653846153846154 |
| Recall@5 | 0.9230769230769231 | 0.8782051282051282 | 0.9423076923076923 |
| Recall@10 | 0.9551282051282052 | 0.9444444444444445 | 1.0 |
| Exact retrieval accuracy | 0.9375 | 0.96875 | 0.96875 |
| Structured retrieval accuracy | 0.92 | 0.92 | 0.92 |
| Semantic retrieval accuracy | 0.5 | 0.5 | 0.5 |
| Hybrid retrieval accuracy | 1.0 | 1.0 | 1.0 |
| Cross-document accuracy | not reported | not reported | 1.0 |
| Provenance accuracy | 1.0 | 0.975 | 1.0 |
| Numeric/aggregation accuracy | NOT_EVALUABLE | NOT_EVALUABLE | NOT_EVALUABLE |

The post-remediation evaluator also retains the original metric names for compatibility: `exact_match_accuracy`, `structured_source_accuracy`, `semantic_source_hit_rate`, and `hybrid_source_hit_rate`.

## Regression comparison

The regression artifact contains one row for every case ID. Summary:

- improved: Q014, Q021, Q036, Q040
- regressed: none
- remaining post-remediation failures: none
- post-remediation failure categories: none

## Source and provenance integrity

The excluded source remains absent from production documents, rows, and pages. Q014 returns only the forensic audit artifact, not the corrupted source as data. PM4 ordering is explicitly unresolved because the corpus has no authoritative ordering evidence. J6 comparison evidence carries source hashes, state, date, report family, and structural metadata. Baseline and pre-remediation artifacts remain preserved.

## Gate rationale

`RETRIEVAL_PROTOTYPE_VALIDATED` is justified here because all 40 cases execute, the fresh artifact is proven, the four demonstrated defects are resolved at the available evidence level, insufficient version evidence and missing answer-level numeric ground truth are explicitly recorded rather than fabricated, no regression was introduced, provenance is correct, the excluded source remains excluded, and all tests pass.
