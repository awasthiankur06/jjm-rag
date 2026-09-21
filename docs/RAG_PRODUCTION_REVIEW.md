# Ground-up RAG production review

## Gate

`RAG_PARTIALLY_VALIDATED`

The authoritative PostgreSQL corpus is healthy and traceable, but the current live production retrieval path did not meet a production-readiness standard in a fresh 40-case evaluation without a semantic provider. This document deliberately distinguishes that result from protected historical prototype metrics.

## Observed architecture

The application uses parser-derived canonical ingestion into PostgreSQL: documents, versions, structured records, observations, canonical content, geography/reporting dimensions, provenance, and ingestion audit. Deterministic structured retrieval is used for numeric questions; exact and lexical retrieval handle identifiers and text. Semantic retrieval and generation are optional provider boundaries, not authorities for facts. The answer layer preserves structured facts, deterministic calculations, and citations.

## Corpus and integrity

- 45 physical sources: 42 HTML-exported XLS files and 3 PDFs.
- 44 production-eligible sources and one blocked corrupted source.
- All manifest source SHA-256 values matched the files at review time.
- `Status of Pipe Water Supply in School (2).xls` remains excluded; its live PostgreSQL production-document count is zero.
- No filename suffix was used as version chronology.

## PostgreSQL validation

The environment-driven local disposable PostgreSQL database reported PostgreSQL 18.6. It contained 44 documents, 44 versions, 34,310 structured records/observations, 3,557 canonical content units, and 37,867 provenance rows. An intentional invalid foreign-key write rolled back fully, leaving no partial document record.

## Fixes in this review

- Source persistence is atomic despite repository-level write methods: a failed source write rolls back all its canonical rows before the caller may log a separate failed audit event.
- SQLite test sessions now enable foreign keys.
- A configured PostgreSQL connection error raises instead of silently substituting SQLite.
- Production evaluation returns an empty semantic channel when semantic retrieval is unavailable, allowing an honest PostgreSQL-only evaluation.

## Live retrieval result

The unchanged 40-case evaluation was run against the live PostgreSQL corpus with exact, lexical, and structured retrieval only. No cloud calls were made.

- Recall@10: 0.453
- Provenance accuracy: 0.975
- Exact retrieval accuracy: 0.125
- Structured retrieval accuracy: 0.160
- Cross-document accuracy: 0.250
- Numeric aggregation correctness: not evaluable from the source-only evaluation contract

This is insufficient for a production-ready gate. The main observed failures were exact retrieval, structured retrieval, cross-document acquisition, and version handling. A configured and independently evaluated semantic backend may improve narrative discovery, but it must not be used to mask structured-retrieval defects.

## Next safe work

1. Build answer-level ground truth for numeric, aggregation, and temporal claims.
2. Diagnose the live PostgreSQL expected-source misses by query class and repair metadata/query contracts generically.
3. Validate semantic retrieval separately against the same unchanged cases before enabling it in the production gate.
4. Re-run the complete suite in an execution environment without the current corpus-validation time limit.
