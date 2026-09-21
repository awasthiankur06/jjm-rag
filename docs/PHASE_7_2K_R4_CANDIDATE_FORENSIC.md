# Phase 7.2K-R4 bounded candidate forensic diagnosis

## Status

`BOUNDED_VALIDATION_ONLY`

The final candidate-forensic batch processed only Q011-Q015. The bounded forensic process is now complete through Q015; Q016-Q040 were not processed.

## Results

- Q011: expected-source miss; earliest loss `FUSION_OR_FINAL_TRUNCATION`.
- Q012: expected-source miss; earliest loss `SEMANTIC_ABSENT_FROM_25`.
- Q013: expected-source miss; earliest loss `SEMANTIC_ABSENT_FROM_25`.
- Q014: expected-source miss; earliest loss `SEMANTIC_ABSENT_FROM_25`; its expected source includes the intentionally excluded corrupted source and an audit artifact, so production exclusion is expected behavior.
- Q015: expected-source hit; `Progress at district level.xls` was present in semantic results and final bounded evidence.

Each case used one Gemini query embedding, one Qdrant search, three PostgreSQL retrieval operations, zero document embeddings, and zero Qdrant writes.

## Consolidated Q001-Q015

The final R1-R4 checkpoint evidence records earlier bounded results; R4 itself records Q011-Q015 as Q015 hit and Q011-Q014 misses.

Expected-source misses: Q004, Q005, Q007, Q010, Q011, Q012, Q013, Q014.

Earliest-loss distribution among misses:

- Fusion/final truncation: 1 in R4 (Q011)
- Semantic absent from 25-point collection: 3 in R4 (Q012-Q014)

This is diagnostic classification, not a scoring adjustment. The current production candidate objects do not expose complete matched-field or normalized-score instrumentation; those fields remain unavailable rather than fabricated. SQL-level predicate tracing is also `SQL_NOT_INSTRUMENTED` in the current production adapter.

## Q015

Q015's semantic expected source was available and survived the bounded final evidence result. The R4 run does not identify a Q015 fusion loss. The earlier Q015 failure remains historical evidence from the prior production regression/fusion state; no retrospective rewrite is made.

## Repeated patterns

- The 25-point semantic scope limits semantic availability for multiple expected sources; this is not a Gemini model failure.
- Structured/exact/lexical candidate relevance remains uneven.
- Multi-source cases can be vulnerable to fusion/truncation.
- Candidate identity was preserved for captured semantic results; no normalization identity loss was observed.
- No production fix was implemented in R4.

## Integrity

- Qdrant collection remains exactly 25 points.
- Unique content IDs remain 25.
- Excluded-source points remain 0.
- Qdrant writes: 0.
- Document embeddings: 0.
- Protected artifacts and corpus hashes unchanged.
- No credentials or model weights introduced.
- Full suite: 46 passed, 1 warning.

Detailed history is in [artifacts/phase7_2_retrieval_forensic_diagnosis.json](../artifacts/phase7_2_retrieval_forensic_diagnosis.json).
