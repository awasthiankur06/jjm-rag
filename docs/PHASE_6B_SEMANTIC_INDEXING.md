# Phase 6B semantic indexing and embedding benchmark

## Gate

`PHASE_6B_PARTIALLY_VALIDATED`

The semantic candidate policy, benchmark reconciliation, provider/index contracts, and model-neutral index prototype are implemented. Actual embedding measurements and pgvector similarity storage are environment-blocked because neither shortlisted model is locally available and PostgreSQL does not have the `vector` extension.

No model download, embedding runtime installation, pgvector installation, Grok call, API, reranker, LangChain, LangGraph, LlamaIndex, or deployment work was performed.

## Phase 6A.2 audit

The canonical PostgreSQL corpus contains 3,557 content units. They represent:

- 315 PDF/OCR page units
- 41 section units
- 41 table units
- 3,460 row units before candidate filtering

Structured cell observations are stored separately in `structured_records` and `observations`; they are not semantic candidates by default.

Canonical source identity is represented by document SHA/document ID and version ID. Provenance is linked through `provenance_records`; geography and reporting metadata are available through their dimension tables.

## Candidate policy

The deterministic policy is implemented in [jjm_rag/semantic/candidates.py](../jjm_rag/semantic/candidates.py) and materialized in [artifacts/phase6b_semantic_candidate_manifest.json](../artifacts/phase6b_semantic_candidate_manifest.json).

Observed result:

- total canonical content units: 3,557
- eligible semantic candidates: 635
- excluded units: 2,922
- numeric-dominant rows excluded: 2,903
- low-information fragments excluded: 16
- identifier-only units excluded: 3
- excluded-source candidates: 0

Candidate types:

- pages: 315
- sections: 41
- tables: 41
- narrative rows: 238

Candidate families:

- policy: 315
- report: 101
- unknown: 40
- template: 39
- sanction: 140

The policy excludes the known corrupted source, empty text, structured units, numeric-only text, identifier-only fragments, and numeric-dominant rows. It retains meaningful narrative rows and document/table/page context.

## Benchmark reconciliation

The preserved semantic benchmark is explicitly reconciled in [artifacts/phase6b_semantic_dataset_reconciliation.json](../artifacts/phase6b_semantic_dataset_reconciliation.json).

The reproducible evidence-backed set contains four cases:

- `Q001`
- `Q002`
- `Q031`
- `Q039`

The earlier eight-case claim is not silently repaired or expanded. Four additional case IDs cannot be reconstructed with query, expected-source, and provenance evidence from protected artifacts, so they remain excluded from model comparison.

## Contracts and prototype

The replaceable contracts are in [jjm_rag/semantic/contracts.py](../jjm_rag/semantic/contracts.py):

- `EmbeddingProvider`
- `SemanticIndex`
- `SemanticDocument`

`SemanticDocument` carries stable content identity, document/version identity, text hash, source family, report type, geography, reporting metadata, provenance, model name/version, dimension, and indexing timestamp.

The model-partitioned prototype is [jjm_rag/semantic/index.py](../jjm_rag/semantic/index.py). It supports deterministic upsert, separate model partitions, metadata filtering, and idempotent logical identity. It does not replace PostgreSQL canonical storage.

## Embedding benchmark

The existing benchmark runner was executed with downloads disabled. Both shortlisted models were blocked:

- BGE-M3: local model path and `FlagEmbedding` runtime unavailable.
- multilingual-e5-large: local model path and `sentence-transformers` runtime unavailable.

No Recall@k, MRR, dimension, latency, or resource result is claimed. See [artifacts/phase6b_embedding_benchmark.json](../artifacts/phase6b_embedding_benchmark.json).

## pgvector

The disposable PostgreSQL 18.6 database was inspected. The `vector` extension was absent. No installation was attempted, so the Phase 6A database was not altered. See [artifacts/phase6b_pgvector_validation.json](../artifacts/phase6b_pgvector_validation.json).

## Retrieval preservation

The Phase 5 retrieval baseline remains protected:

- 40 cases
- Recall@10: 1.0
- cross-document accuracy: 1.0
- provenance accuracy: 1.0
- zero regressions

The existing evaluator was rerun to a temporary output and matched the protected post-remediation metrics exactly across 40 cases. The new semantic prototype was not connected to that retrieval path, so no semantic improvement claim is made and exact/structured/hybrid retrieval remains untouched.

## Tests and security

Focused Phase 6B tests pass: 3 passed. The full suite baseline remains green from Phase 6A.2 validation: 29 passed, 1 warning.

The preservation/security scan verified protected artifact hashes, corpus hashes, excluded-source status, absence of the plaintext credential, and no generated temporary runner was retained in the final Phase 6B artifact set.

## Required remaining work

- provide an approved local copy of at least one shortlisted embedding model and runtime;
- rerun the four-case evidence-backed benchmark for each available model;
- provision pgvector separately or validate another approved vector adapter without changing canonical PostgreSQL truth;
- run semantic retrieval regression only after actual embeddings are available.

The exact machine-readable Phase 6B identity is in [artifacts/phase6b_baseline_identity.json](../artifacts/phase6b_baseline_identity.json).
