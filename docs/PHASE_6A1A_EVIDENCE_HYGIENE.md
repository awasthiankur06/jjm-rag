# Phase 6A.1A evidence hygiene

## Final gate

`PHASE_6A1A_PARTIALLY_VALIDATED`

The Phase 5B.1 test/artifact contract is corrected and the full suite passes. The historical baseline-hash discrepancy remains conservatively classified as `D_UNRESOLVED` because this workspace has no Git history or prior artifact bytes. PostgreSQL remains environment-blocked; no PostgreSQL integration evidence was fabricated.

## Initial state

Before editing:

- Git revision/status: unavailable; `d:\jjm-rag` is not a Git worktree.
- Full pytest: 27 total, 26 passed, 1 failed, 0 skipped, 1 warning.
- Failing test: [tests/test_phase5b1_dataset_integrity.py](../tests/test_phase5b1_dataset_integrity.py).
- Historical artifact: [artifacts/phase5b1_dataset_integrity.json](../artifacts/phase5b1_dataset_integrity.json).

The preserved artifact stores dataset fields under `dataset_summary` and runner status under `runner_contract`. The test incorrectly read those fields at the top level.

## Correction

Only [tests/test_phase5b1_dataset_integrity.py](../tests/test_phase5b1_dataset_integrity.py) was corrected. It now:

- reads `dataset_summary.semantic_case_count`;
- reads `dataset_summary.candidate_count`;
- reads `runner_contract.runner_contract_ok`;
- validates the semantic case count against the artifact's retained case IDs;
- validates candidate count against the artifact's unique-unit count.

The historical Phase 5B.1 artifact was not changed, and the test was not weakened or skipped.

## Test results

Targeted test:

```text
python -m pytest -q tests/test_phase5b1_dataset_integrity.py
1 passed
```

Full suite:

```text
python -m pytest -q
27 passed, 1 warning
```

The warning is the existing PyPDF2 deprecation warning.

## Baseline-hash investigation

The Phase 6A identity records this expected hash for `artifacts/phase5_baseline_identity.json`:

```text
e1d5a5d5b1fdc5e72d22d0c8a97fc0c18f04b6240b0f2954c9c242f6a01d2250
```

A fresh read-only SHA-256 of the current protected file is:

```text
b26db5198ca6415ecc1c4b7dd16654836c16a2c0ec27ef57e9bd5a8d002f3ddb
```

Sources:

- expected value: `artifacts/phase6a_baseline_identity.json`, `baseline_files.artifacts/phase5_baseline_identity.json.sha256`;
- actual value: SHA-256 calculated from the current file bytes.

Classification: `D_UNRESOLVED`.

The workspace has no Git repository, commit history, or prior blob for either file. The Phase 5 artifact embeds `2026-09-08T11:48:49.098817+00:00`; the Phase 6A identity embeds `2026-09-08T00:00:00Z`. Filesystem modification times place the Phase 5 file before the Phase 6A identity, but filesystem metadata cannot establish reliable content chronology. The previous bytes are unavailable, so the evidence cannot distinguish a stale Phase 6A reference from a later legitimate or non-material Phase 5 artifact rewrite.

Neither historical artifact was modified.

## Preservation audit

- Protected Phase 5 artifact hashes remained unchanged during this task.
- The Phase 5 artifact's own internal hashes match the current protected retrieval artifacts.
- Corpus hashes match `corpus_manifest_final.json`.
- Physical corpus count remains 45.
- Production-eligible count remains 44.
- Excluded count remains 1.
- `Status of Pipe Water Supply in School (2).xls` remains physically preserved, excluded from production ingestion, excluded from indexing, and absent from production records.
- Retrieval evaluation remains unchanged.
- Post-remediation regression evidence remains unchanged.
- Query evaluation cases remain unchanged.
- No retrieval source code changed.
- No Phase 6A PostgreSQL code was expanded.

## PostgreSQL status

PostgreSQL integration remains `POSTGRES_INTEGRATION_BLOCKED_BY_ENVIRONMENT`. No PostgreSQL server, client binaries, Docker, Docker Compose, driver, or configured DSN is available. This task did not install or start infrastructure, run fake PostgreSQL tests, substitute SQLite, or fabricate integration evidence.

## Files changed

- [tests/test_phase5b1_dataset_integrity.py](../tests/test_phase5b1_dataset_integrity.py)
- [artifacts/phase6a1a_evidence_hygiene.json](../artifacts/phase6a1a_evidence_hygiene.json)
- [docs/PHASE_6A1A_EVIDENCE_HYGIENE.md](../docs/PHASE_6A1A_EVIDENCE_HYGIENE.md)

## Files intentionally unchanged

All protected Phase 5 artifacts, `artifacts/phase6a_baseline_identity.json`, all corpus files, retrieval implementation, retrieval cases and metrics, the excluded source, and Phase 6A PostgreSQL implementation remain unchanged.
