# Production Technology Decision

## Gate

`PRODUCTION_TECHNOLOGY_SELECTION_PARTIALLY_READY`

This phase selects a production direction for the validated retrieval architecture. It does not claim that the complete RAG system is production-ready and does not build the chatbot or API.

## Recommended architecture

1. **Query interpretation/routing**: custom Python typed router.
2. **Exact retrieval**: PostgreSQL B-tree indexes and PostgreSQL full-text search over normalized names, codes, identifiers, hashes, and metadata.
3. **Structured retrieval**: PostgreSQL normalized report, snapshot, table, row, metric, geography, date, and value tables.
4. **Semantic retrieval**: BGE-M3, initially benchmarked locally, stored in pgvector; multilingual-e5-large remains the comparison candidate.
5. **Cross-document alignment**: custom Python dimension-aware alignment over PostgreSQL keys and schema fingerprints.
6. **Evidence fusion**: custom Python typed evidence fusion with route-specific precedence.
7. **Evidence validation**: custom Python provenance, eligibility, schema, period, and insufficiency validation.
8. **Deterministic computation**: PostgreSQL SQL plus Python validation for aggregation, ranking, and comparison.
9. **Answer generation**: xAI Grok 4.6 candidate, behind an interface and strict evidence contract.
10. **Citation/provenance validation**: custom Python validator requiring source hash and smallest useful page/table/row/column citation.
11. **Observability/evaluation**: structured application logs, PostgreSQL audit fields, OpenTelemetry-compatible traces, and the existing 40-case regression suite.

## Selected versus unresolved decisions

| Component | Status | Rationale |
|---|---|---|
| PostgreSQL structured source of truth | SELECTED | Best fit for deterministic tabular computation, joins, provenance, dates, versions, and auditability. |
| PostgreSQL B-tree + FTS exact retrieval | SELECTED | Current exact retrieval is 0.96875; a separate search engine is not demonstrated as necessary. |
| PostgreSQL + pgvector | SELECTED direction | Keeps semantic and structured metadata together, but must be benchmarked on JJM embeddings and filters. |
| xAI Grok 4.6 | SHORTLISTED | Required target and documented capability fit; live generation benchmark requires credentials and policy approval. |
| BGE-M3 | SHORTLISTED | Strong documented multilingual/hybrid features; JJM semantic quality remains unmeasured. |
| multilingual-e5-large | SHORTLISTED | Strong documented multilingual retrieval candidate; 512-token limit makes chunking/truncation a benchmark concern. |
| Reranker | NOT_REQUIRED initially | Recall@10 and hybrid retrieval are both 1.0; top-1 quality does not yet justify added cost. |
| Custom Python orchestration | SELECTED | Directly matches the validated architecture and preserves testability. |
| FastAPI | REQUIRES_EXTERNAL_DECISION | Likely fit, but deployment/auth/SLO decisions are outside this phase. |
| LangChain/LangGraph/LlamaIndex | NOT_REQUIRED | No concrete integration problem has been demonstrated. |

## Cost drivers

Known: xAI publishes model token prices. For Grok 4.6, the current xAI model page lists $2 per million input tokens and $6 per million output tokens below the long-context threshold, with separate higher-tier pricing for long prompts.

Formula:

`monthly_generation_cost = queries * ((input_tokens / 1,000,000) * input_price + (output_tokens / 1,000,000) * output_price)`

Other drivers are embedding refresh compute, PostgreSQL/pgvector compute and storage, backups, API hosting, observability, secrets management, and support. No traffic, SLO, retention, or concurrency figures were provided, so no total monthly estimate is asserted.

## Rejected or deferred technologies

- **LangChain**: rejected for this phase because it does not replace deterministic structured computation or provenance validation.
- **LangGraph**: rejected because no durable stateful workflow or human approval loop is demonstrated.
- **LlamaIndex**: rejected because document abstractions do not remove custom table/schema alignment requirements.
- **Dedicated vector database**: deferred; current corpus size and benchmark do not demonstrate need for a second datastore.
- **OpenSearch/Qdrant/Pinecone**: retained as fallback candidates for a future scale/filter/operations benchmark.
- **Reranker**: not justified until a JJM-specific top-1 quality test shows material benefit.

## What remains before implementation

- Run the controlled Grok generation benchmark with approved credentials and data-transfer policy.
- Benchmark BGE-M3 against multilingual-e5-large on representative JJM policy, OCR, report-description, and metadata queries.
- Test pgvector exact/HNSW behavior with state/report/date filters and provenance joins.
- Define production traffic, latency, availability, retention, and recovery objectives.
- Obtain security approval for external LLM data transfer and secret management.
- Add answer-level numeric and citation ground truth beyond the current source-level 40-case benchmark.

## Phase 5 recommendation

Implement only the production data/evidence contracts and isolated technology benchmarks first: PostgreSQL schema, pgvector experiment, embedding comparison, Grok generation harness, citation validator, and observability contract. Do not build the end-user chatbot until those gates are resolved.

## Phase 5 benchmark update

| Layer | Technology | Evidence | Confidence | Decision |
|---|---|---|---|---|
| LLM | xAI Grok 4.6 | DOCUMENTED; live run blocked by missing `XAI_API_KEY` | Medium for capability fit, low for JJM behavior | REQUIRES_BENCHMARK |
| Embeddings | BGE-M3 versus multilingual-e5-large | DOCUMENTED candidates; local model runtimes unavailable | Low until JJM semantic benchmark runs | BENCHMARK_INCONCLUSIVE |
| Structured DB | PostgreSQL | OBSERVED corpus fit; DOCUMENTED relational/security capabilities | High for current logical workload | SELECTED |
| Vector store | PostgreSQL + pgvector | DOCUMENTED capabilities; local PostgreSQL benchmark blocked | Medium for direction, low for measured performance | REQUIRES_BENCHMARK |
| Exact retrieval | PostgreSQL B-tree + FTS | BENCHMARKED exact retrieval accuracy 0.96875 | High for current corpus | SELECTED |
| Reranker | None initially | BENCHMARKED Recall@10 1.0 and hybrid accuracy 1.0; reranker not run | Medium | NOT_JUSTIFIED |
| Orchestration | Custom Python | OBSERVED implementation and 23 passing tests; frameworks unavailable | High for current workflow | CUSTOM_PREFERRED |
| API | FastAPI candidate | INFERRED fit; deployment/SLO inputs absent | Low | REQUIRES_EXTERNAL_DECISION |

The updated final gate is:

`PRODUCTION_TECHNOLOGY_SELECTION_PARTIALLY_READY`

The direction is clear, but production implementation remains blocked on the Grok generation benchmark, the embedding comparison, the local pgvector benchmark, and external security/deployment decisions.
