# Residual Failure Diagnosis

## Fresh proof status

The fresh 40-case evaluation was executed successfully and is the authoritative evidence set. The generated artifact is `artifacts/retrieval_evaluation_results.json`, and the summary confirms:

- case_count = 40
- executed = 40
- routing_accuracy = 0.85
- recall_at_10 = 0.9444444444444445
- failure categories = EXACT_RETRIEVAL: 1, VERSION_HANDLING: 2, CROSS_DOCUMENT_ALIGNMENT: 1

The evaluation gate remains:

> RETRIEVAL_ARCHITECTURE_REQUIRES_REVISION

This gate is intentionally preserved. The system is not prototype-validated and should not move forward to production technology selection.

## Residual failing cases

### Q014 — EXACT_RETRIEVAL_DEFECT

This is a provenance and exact-match failure. The query required the exact source `Status of Pipe Water Supply in School (2).xls` together with the forensic provenance artifact `artifacts/status_pipe_water_forensic.json` and the required SHA-256 filter. The system instead returned unrelated school-water and public-institution reports, which indicates it did not enforce the required exact-match and provenance constraints.

The issue is real and should be treated as a fix-now item within the controlled evaluation path. The excluded source is intentionally quarantined and must never be treated as valid corpus evidence.

### Q021 — VERSION_EVIDENCE_DEFECT

This was not a zero-run problem. It is a version-semantics issue. The PM4 family contains multiple state-scoped snapshots such as Maharashtra, Tamil Nadu, Punjab, and Andaman & Nicobar Islands. The correct interpretation is that these are different state snapshots of the same report family, not duplicates or a single version determined by filename suffices alone.

The system must compare state scope, content, and report metadata, not infer version lineage from `(1)`, `(2)`, `(3)`, or similar suffixes.

### Q036 — CROSS_DOCUMENT_ALIGNMENT_DEFECT

This query required comparing beneficiary-verification records across Assam, Maharashtra, and Tamil Nadu for a common date and schema. The retrieval stage could locate the right J6 family, but the comparison logic did not preserve schema alignment across the state-scoped documents.

This is a genuine cross-document alignment defect and should be treated as a design-level issue requiring a schema-aware comparison layer. It is not a broad retrieval rewrite, but it remains a real architecture concern.

### Q040 — VERSION_EVIDENCE_DEFECT

The answer is no: the corpus cannot establish the latest PM4 version from filename suffixes alone. The PM4 files are state-specific report snapshots, and the latest version must be established through content comparison, state scope, metadata, and provenance, not from filename labels alone.

This remains a version-provenance question, not a simple exact-source retrieval bug.

## Baseline comparison

The fresh run did not change the architecture gate. The targeted remediation is present and the evaluation path itself is proven valid. The remaining four failures are not evidence that the evaluator is broken; they are a remaining set of semantic and architectural issues to classify and retain as the gate condition.

## Final disposition

The final gate remains:

> RETRIEVAL_ARCHITECTURE_REQUIRES_REVISION

No broad retrieval rewrite was performed. No prototype validation claim was made. The work ends with evidence-preserved diagnosis rather than productionization.
