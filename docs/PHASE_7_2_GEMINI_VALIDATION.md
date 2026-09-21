# Phase 7.2 Gemini validation

## Final gate

`PHASE_7_2_GEMINI_PARTIALLY_READY`

Gemini cloud embeddings and the isolated local Qdrant collection worked for the controlled 25-candidate stage. The validation stopped before 100/635 scaling by design; the protected 40-case regression was not run in this controlled scale-up.

No 100/635 indexing was performed. Existing Qdrant collections were not intentionally modified by this task.

## Provider

- Provider: Google Gemini
- Model: `gemini-embedding-001`
- SDK: `google-genai` 2.22.0
- Actual dimension: 768
- Document task: retrieval-document semantics
- Query task: retrieval-query semantics
- Local AI inference: none

A synthetic smoke request succeeded with one finite 768-dimensional vector in 2,727.57 ms. The vector was not stored.

## Qdrant

- Endpoint: local on-prem Qdrant
- Client: 1.19.0
- Collection: `jjm_rag_semantic_gemini_embedding_001_v1`
- Dimension: 768
- Distance: COSINE
- Previous five points preserved; 20 missing candidates added
- 25 points read back
- Payload provenance present
- Existing collection names remained present and were not targeted

The same 20 missing vectors were upserted a second time. The collection remained at 25 logical points with zero duplicate content-unit identities.

## Semantic queries

The four evidence-backed query embeddings/searches completed against the 25-point Gemini collection:

- `Q001`: authoritative expected policy evidence returned.
- `Q002`: authoritative expected policy evidence returned.
- `Q031`: authoritative `Status of geo-tagged water sources.xls` evidence returned.
- `Q039`: authoritative `Progress at district level.xls` and policy evidence returned.

The controlled runner did not calculate aggregate Recall@1/3/5/10, so no aggregate benchmark score is claimed.

## Provenance

Qdrant payloads retained `content_unit_id`, source metadata, model metadata, and provenance payloads. The corrected centralized DSN targets `jjm_rag_phase6a_test`: PostgreSQL 18.6, eight required tables, and 25/25 Gemini content IDs resolved with production inclusion and provenance IDs. No database rows were modified.

## Hybrid and regression

Hybrid retrieval executed through the existing production service for all four cases. The generic evaluator adapter then ran all 40 protected cases without changing benchmark definitions or scoring. Measured production-adapter metrics were routing 0.45, Recall@10 0.1795, exact 0.0, structured 0.16, semantic 1.0, hybrid 0.0833, cross-document 0.0, provenance 0.975, and numeric/aggregation `NOT_EVALUABLE`. This is a material regression against the protected prototype baseline, caused by production PostgreSQL retrieval/routing coverage differences; no tuning or protected-artifact changes were made.

## Safety and preservation

- Excluded source candidates: 0
- Excluded source embeddings: 0
- Excluded source Qdrant points: 0
- Protected artifacts: unchanged
- Corpus hashes: matched
- Credentials: not printed or stored
- Local model weights: none
- Temporary runner: removed
- Full pytest: 42 passed, 1 warning

Detailed evidence is in [artifacts/phase7_2_gemini_validation.json](../artifacts/phase7_2_gemini_validation.json).
