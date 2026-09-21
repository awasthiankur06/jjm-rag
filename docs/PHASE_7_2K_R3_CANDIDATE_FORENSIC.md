# Phase 7.2K-R3 bounded candidate forensic diagnosis

## Status

`BOUNDED_VALIDATION_ONLY`

Only Q007-Q010 were processed. No production retrieval code, benchmark, corpus, PostgreSQL data, or Qdrant data was changed.

## Execution budget

- Gemini query calls: 4
- Qdrant searches: 4
- PostgreSQL operations: 12 total
- Document embeddings: 0
- Qdrant writes: 0
- Candidate count per channel: 10
- Rate limits: none

## Results

### Q007

- Expected: `CS1 B(i). Water Quality.xls`
- Expected source absent from the 25-point semantic collection.
- Earliest loss: `SEMANTIC_ABSENT_FROM_25`.
- Production non-semantic channels did not preserve the expected source.

### Q008

- Expected: `CS1 B (ii). Robust chlorination system_ Disinfecti.xls`
- Expected source absent from the 25-point semantic collection.
- Earliest classification: `SEMANTIC_ABSENT_FROM_25`.
- Expected source still survived production non-semantic retrieval/fusion.

### Q009

- Expected: `District wise number of Rural Population as on (01 (1).xls`
- Expected source absent from the 25-point semantic collection.
- Earliest classification: `SEMANTIC_ABSENT_FROM_25`.
- Expected source survived production non-semantic retrieval/fusion.

### Q010

- Expected four rural-population report sources.
- Expected sources were not present in the 25-point semantic collection.
- Some expected sources entered production candidate paths, but the complete multi-source set was lost at `FUSION_OR_FINAL_TRUNCATION`.

## Comparison with prior stages

R1/R2/R3 now show repeated patterns:

- expected sources outside the 25-point collection are not evidence of Gemini failure;
- non-semantic PostgreSQL paths can preserve some expected sources even when semantic evidence is absent;
- multi-source comparison queries such as Q010 remain vulnerable to final fusion/truncation loss;
- all channels consistently return bounded ten-candidate sets, but candidate relevance/specificity remains uneven.

## Integrity

- Gemini collection remains at 25 logical points.
- Excluded-source points remain 0.
- Qdrant writes: 0.
- Document embeddings: 0.
- Protected artifacts and corpus hashes unchanged.
- Full tests remain required after this bounded run.
