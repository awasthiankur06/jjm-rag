# Qdrant canonical-sync review

## Result

The local active collection `jjm_rag_semantic_gemini_embedding_001_v1` is
reachable and structurally compatible with Gemini embeddings (768 dimensions,
cosine distance).  It contains 635 points.  After the canonical PostgreSQL
header repair, however, only 545 of those point IDs resolve to current
canonical content and only 367 payload texts exactly match current canonical
text.  The existing collection is therefore stale derived data.

The corrupted workbook remains absent from Qdrant.

## Safety repair

`CanonicalValidatedQdrantRetriever` now resolves every returned point against
PostgreSQL before admitting it as evidence.  It rejects a point when its
`content_unit_id` is missing or its payload text differs from the current
canonical text.  If the embedding provider is unavailable, the RAG service
continues with deterministic PostgreSQL retrieval and reports that semantic
evidence was unavailable.

## Replacement index

`artifacts/semantic_candidate_manifest_post_header_repair.json` was generated
from the repaired PostgreSQL corpus.  It contains 545 eligible semantic
candidates from 3,466 canonical units and zero candidates from the excluded
source.

A new local collection,
`jjm_rag_semantic_gemini_embedding_001_v2_header_repair`, was created and
populated as a safe replacement.  A refused inherited localhost-proxy
environment variable caused the initial `ProviderError`; Gemini now explicitly
bypasses inherited proxy environment variables because Windows is configured
for direct access.  The full index completed with 545 embeddings and upserts,
69 successful batches, and zero provider failures or rate-limit retries.

Every replacement point was read back and validated: 545 current PostgreSQL
content IDs, 545 exact canonical-text matches, 545 768-dimensional vectors,
545 deterministic point IDs, and zero excluded-source points.  The active
`QDRANT_COLLECTION` setting now points to the replacement collection.  The
former v1 collection was retained for rollback and was not deleted.

## Required completion step

The next retrieval task is to measure semantic and hybrid retrieval against the
40-case contract using this synchronized index.  Do not delete the old
collection until that evaluation passes.
