# Phase 7.2K-R2 bounded candidate forensic diagnosis

## Status

`BOUNDED_VALIDATION_ONLY`

Only Q004-Q006 were processed with the existing bounded runner. No production retrieval code, benchmark, corpus, PostgreSQL data, or Qdrant data was changed.

## Execution budget

- Gemini query calls: 3
- Qdrant searches: 3
- PostgreSQL operations: 9 total
- Document embeddings: 0
- Qdrant writes: 0
- Candidate count per channel: 10
- Rate limits: none

## Results

### Q004

- Expected source: `CS1 A. Coverage.xls`
- Active channels: exact, structured, lexical, semantic
- Expected source absent from the 25-point Qdrant subset
- Earliest observed loss: `FUSION_OR_FINAL_TRUNCATION`
- The expected source was available in production PostgreSQL/channel candidate behavior but was not retained in final fused evidence.

### Q005

- Expected source: `CS1 A. Coverage.xls`
- Active channels: exact, structured, lexical, semantic
- Expected source absent from the 25-point Qdrant subset
- Earliest observed loss: `SEMANTIC_ABSENT_FROM_25`
- No Gemini failure is inferred from this absence.

### Q006

- Expected source: `CS1 A. Coverage.xls`
- Active channels: exact, structured, lexical, semantic
- Expected source absent from the 25-point Qdrant subset
- Earliest classification: `SEMANTIC_ABSENT_FROM_25`
- The case still returned the expected source through production non-semantic candidate paths.

## Comparison with R1

R1 established Q001-Q003 candidate-level behavior. R2 extends the same capture contract to Q004-Q006. Repeated patterns now include:

- all channels return bounded candidate sets, but exact/structured/lexical candidates can be generic or unrelated;
- semantic absence from the 25-point subset is distinct from a Gemini retrieval failure;
- Q004 demonstrates evidence can enter production paths but disappear at fusion/final truncation;
- Q006 demonstrates expected evidence can be returned without semantic Qdrant presence.

## Integrity

- Gemini collection remains at 25 logical points.
- Excluded-source points remain 0.
- Qdrant writes: 0.
- Document embeddings: 0.
- Protected artifacts and corpus hashes unchanged.
- Full suite remains required after the bounded run.
