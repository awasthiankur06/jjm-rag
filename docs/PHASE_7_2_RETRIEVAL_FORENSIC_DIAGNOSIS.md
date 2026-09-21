# Phase 7.2H-R1 bounded forensic diagnosis

## Status

`BOUNDED_VALIDATION_ONLY`

The prior forensic runner was unbounded and could make repeated Gemini/Qdrant calls per case. It has been replaced with a checkpointed runner supporting `--start-case`, `--end-case`, `--max-cases`, `--resume`, and `--no-resume`.

## Bounded behavior

Per case:

- maximum Gemini query embeddings: 1
- Qdrant searches: 1
- PostgreSQL retrieval operations: bounded production paths
- document embeddings: 0
- Qdrant writes: 0
- progress is persisted after every completed case
- rate-limit failures are not retried indefinitely

Checkpoint: `tmp/phase7_2_forensic_checkpoint.json`

Result: `tmp/phase7_2_forensic_result.json`

## First validation run

Only cases 1-5 were executed:

- Q001: completed, expected source miss
- Q002: completed, expected source miss
- Q003: completed, expected source miss
- Q004: completed, expected source miss
- Q005: completed, expected source hit

Each case used exactly one Gemini query embedding, one Qdrant search, and three bounded PostgreSQL retrieval operations. No rate limit occurred.

## Resume validation

`--resume --max-cases 5` skipped all five completed cases:

- Q001
- Q002
- Q003
- Q004
- Q005

New Gemini calls: 0. New Qdrant searches: 0.

## Interpretation

The first five cases reproduce the known production-path discrepancy: semantic retrieval is available, but production fusion/routing/exact/structured coverage does not match the protected prototype path. No retrieval logic, thresholds, cases, or baselines were changed.

The full 40-case forensic diagnosis is not complete. Cases 6-40 remain pending and must be resumed in bounded batches only with explicit approval.

## Q006-Q015 continuation

Cases Q006 through Q015 were completed in the second bounded batch:

- 10 Gemini query calls
- 10 Qdrant searches
- 0 document embeddings
- 0 Qdrant writes
- no rate limiting

Observed patterns:

- Production exact retrieval returned no expected source for all Q006-Q015.
- Production lexical retrieval returned no results for all Q006-Q015.
- Production structured retrieval repeatedly returned the same unrelated generic source set.
- Routing mismatched the benchmark query type for Q006, Q007, Q009, Q010, Q011, Q012, Q014, and Q015.
- Q006-Q014 expected evidence was absent from the current 25-point Gemini collection.
- Q015 expected `Progress at district level.xls` was present semantically, but production fusion retained unrelated structured evidence above it.

The evidence currently points to a combination of PostgreSQL exact/lexical/structured coverage gaps, routing mismatches, and fusion/truncation behavior. It does not indicate a Gemini provider failure. No fixes were made in this diagnosis phase.

## Remediation attempt

The smallest general fixes were applied:

- token-aware exact/lexical PostgreSQL predicates;
- structured query-term coverage across persisted document/record/content fields;
- broader deterministic routing vocabulary;
- rank-normalized fusion across retrieval channels;
- Qdrant client 1.19 compatibility and canonical `content_unit_id` mapping.

Focused tests passed. The bounded Q001-Q015 rerun measured expected-source hits before remediation only for Q005 and Q015, and after remediation for Q003, Q004, Q006, and Q008. Remaining misses were Q001, Q002, Q005, Q007, Q009, Q010, Q011, Q012, Q013, Q014, and Q015. Q015 regressed after fusion normalization, so no further tuning was attempted.

This confirms the remediation direction is general but incomplete. PostgreSQL source/field coverage and production fusion still require dedicated diagnosis. Gemini semantic retrieval remains operational; it is not identified as the root cause.

## Integrity

- Gemini collection remains at 25 points.
- Qdrant writes: 0.
- Document embeddings: 0.
- Excluded-source points: 0.
- Protected artifacts unchanged.
- Corpus hashes matched.
- No secrets exposed.

Detailed machine-readable evidence is in [artifacts/phase7_2_retrieval_forensic_diagnosis.json](../artifacts/phase7_2_retrieval_forensic_diagnosis.json).
