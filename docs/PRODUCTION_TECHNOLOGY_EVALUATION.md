# Production Technology Evaluation

## Scope and evidence discipline

This phase evaluates technologies for the already validated logical retrieval architecture. It does not redesign retrieval and does not build a chatbot or production deployment.

Evidence labels used throughout:

- **OBSERVED**: measured or directly counted in this repository.
- **BENCHMARKED**: measured by the validated 40-case evaluation or an explicitly run local test.
- **DOCUMENTED**: stated in current vendor/project documentation.
- **INFERRED**: engineering conclusion derived from the observed corpus and documented capability.
- **UNKNOWN**: not established by this phase.

## Corpus fit

The manifest contains 45 physical files, 44 production-usable sources, 1 excluded corrupted source, 44 extracted documents, 3,042 structured rows, 334 PDF pages, and 378 semantic units. The corpus mixes policy PDFs, OCR text, HTML/XLS exports, report metadata, state/district scopes, report families, numeric tables, identifiers, hashes, and version evidence.

The post-remediation benchmark is 40/40 executed with Recall@10 = 1.0, cross-document accuracy = 1.0, provenance accuracy = 1.0, exact retrieval accuracy = 0.96875, structured retrieval accuracy = 0.92, and hybrid retrieval accuracy = 1.0. Numeric/aggregation accuracy remains `NOT_EVALUABLE` because the current cases do not provide answer-level expected values for every aggregation.

## Technology matrix

| Component | Candidate | Evidence | Advantages | Risks | Cost/complexity | Decision |
|---|---|---|---|---|---|---|
| LLM generation | xAI Grok 4.6 | DOCUMENTED, UNKNOWN | Required project target; 500k context; structured outputs; function calling | Live grounding, citation fidelity, abstention, latency, and failure behavior are not tested | xAI documents $2/M input and $6/M output below 200k prompt tokens, with higher long-context tier; traffic is unknown | SHORTLISTED; live benchmark required |
| LLM alternatives | Grok 4.5, Grok 4.3, Grok 4.20 variants | DOCUMENTED | Lower-cost or larger-context alternatives may fit different latency/cost envelopes | No JJM generation comparison | Must compare response quality, cost, latency, and structured-output behavior | REQUIRES_BENCHMARK |
| Embeddings | BAAI/bge-m3 | DOCUMENTED, INFERRED, UNKNOWN | 1024 dimensions, 8192-token limit, multilingual, dense/sparse/multi-vector modes | No JJM-specific semantic benchmark; local serving cost unknown | Self-hosted compute and model lifecycle | SHORTLISTED; JJM benchmark required |
| Embeddings | multilingual-e5-large | DOCUMENTED, INFERRED, UNKNOWN | 1024 dimensions, 100-language support, retrieval-trained query/passage prefixes | 512-token limit; no JJM-specific benchmark; low-resource language quality may vary | Self-hosted compute; truncation risk for long policy units | SHORTLISTED; compare against BGE-M3 |
| Embeddings | hosted proprietary embedding API | UNKNOWN | Potentially low operations burden | API dependency, data transfer, reproducibility, cost, policy approval | Requires vendor and privacy decision | REQUIRES_EXTERNAL_DECISION |
| Structured source of truth | PostgreSQL | OBSERVED, DOCUMENTED, INFERRED | Joins, dates, numeric aggregation, transactions, auditability, backups, provenance relationships | Requires schema and operations ownership | One relational deployment; provider cost unknown | SELECTED |
| Vector/semantic store | PostgreSQL + pgvector | DOCUMENTED, INFERRED | Exact or approximate vector search, HNSW/IVFFlat, metadata filtering, hybrid FTS, WAL/PITR ecosystem | Filtered approximate-search tuning and JJM embedding benchmark remain | Lower operational surface than a second datastore | SELECTED for initial production benchmark |
| Dedicated vector DB | Qdrant, Pinecone, OpenSearch, other | DOCUMENTED, INFERRED | Strong vector-specific features and managed options | Adds a second source of truth; provenance joins and deterministic tables remain custom; no demonstrated need at current scale | Extra service, backup, security, and observability surface | DEFERRED |
| Exact retrieval | PostgreSQL B-tree plus PostgreSQL FTS | OBSERVED, BENCHMARKED, DOCUMENTED | Deterministic exact identifiers, hashes, filenames, format codes, filtered metadata | Very large future corpus or fuzzy multilingual requirements may change decision | Low incremental complexity with PostgreSQL | SELECTED |
| Reranking | None initially | BENCHMARKED, INFERRED | Recall@10 = 1.0 and hybrid = 1.0; avoids added latency/model cost | Recall@1 = 0.4957; top-1 user experience is not fully evaluated | No added runtime service | NOT_JUSTIFIED initially |
| Orchestration | Custom lightweight Python | OBSERVED, BENCHMARKED, INFERRED | Direct mapping to validated router, exact, structured, semantic, alignment, evidence, and computation layers | Team owns retries, tracing, contracts, and tool loops | Lowest lock-in and dependency complexity | SELECTED |
| Framework | LangChain | DOCUMENTED, INFERRED | Integrations and model/tool abstractions | Does not solve numeric correctness, schema alignment, or provenance; abstraction overhead | Additional dependency and upgrade surface | NOT_SELECTED |
| Framework | LangGraph | DOCUMENTED, INFERRED | Stateful graph workflows and resumability | No demonstrated stateful workflow requirement; complexity is premature | Additional graph state/testing burden | NOT_SELECTED |
| Framework | LlamaIndex | DOCUMENTED, INFERRED | Document/index abstractions and connectors | Table semantics, exact identifiers, and provenance still require custom logic | Coupling and duplicated abstractions | NOT_SELECTED |
| API | FastAPI | INFERRED, UNKNOWN | Fits Python services, typed contracts, async external calls, OpenAPI | Deployment, authentication, and SLO requirements not decided | Low application complexity; hosting unknown | SHORTLISTED |

## Content routing implications

### Embeddings are appropriate for

- policy guidance passages and explanatory PDF sections;
- OCR text where paraphrase and terminology variation matter;
- report descriptions and narrative metadata;
- semantic discovery across report families;
- multilingual or paraphrased government terminology after JJM-specific testing.

### Embeddings must not be the primary mechanism for

- filenames, format codes, hashes, sanction numbers, scheme IDs, and exact identifiers;
- numeric values, totals, rankings, filters, and date/financial-year constraints;
- row/column selection or schema alignment;
- excluded-source eligibility and provenance validation;
- version precedence, especially where filename suffixes are not evidence.

The production design should preserve exact, structured, and semantic branches separately and fuse only typed evidence.

## Vector and structured-store comparison

PostgreSQL plus pgvector is the initial recommendation because the corpus is small enough that a second vector service has not been justified and the hardest requirements are relational: state/district filtering, report snapshots, row/column provenance, deterministic calculations, and version metadata. pgvector documents exact nearest-neighbor search, HNSW and IVFFlat approximate indexes, metadata filtering, hybrid search with PostgreSQL FTS, and PostgreSQL WAL/point-in-time recovery compatibility.

Qdrant is a credible later candidate when vector-specific scaling, payload filtering, or independent vector operations become a demonstrated need. OpenSearch is credible when full-text, hybrid search, and search-cluster operations become primary requirements. Pinecone is credible when a managed vector service is preferred. None is selected now because no JJM benchmark or production traffic input demonstrates that the additional datastore outweighs provenance and operations complexity.

## Reranking decision

Decision: `NOT_JUSTIFIED` initially.

The benchmark shows Recall@10 = 1.0 and hybrid retrieval = 1.0. Recall@1 is 0.4957, so a later cross-encoder experiment is reasonable if product requirements demand better first-result ordering. It is not justified merely because rerankers are common. The trigger for that experiment is a JJM top-1/top-3 answer-quality benchmark showing a material user-facing benefit after metadata filtering.

## Framework decision

Custom Python orchestration is selected. LangChain, LangGraph, and LlamaIndex are not required to implement the validated logical pipeline. A framework may be reconsidered only after a concrete need appears for durable state, complex tool routing, human approval, or distributed workflow recovery.

## Official/documented references

- xAI models and pricing: https://docs.x.ai/docs/models
- xAI structured outputs: https://docs.x.ai/docs/guides/structured-outputs
- xAI function calling: https://docs.x.ai/docs/guides/function-calling
- pgvector capabilities and indexing: https://github.com/pgvector/pgvector
- PostgreSQL full-text search: https://www.postgresql.org/docs/current/textsearch.html
- PostgreSQL row-level security: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- BGE-M3 model card: https://huggingface.co/BAAI/bge-m3
- multilingual-e5-large model card: https://huggingface.co/intfloat/multilingual-e5-large
- Qdrant documentation: https://qdrant.tech/documentation/
- OpenSearch vector search: https://docs.opensearch.org/latest/vector-search/
- Pinecone documentation: https://docs.pinecone.io/guides/get-started/overview

## Readiness gate

`PRODUCTION_TECHNOLOGY_SELECTION_PARTIALLY_READY`

The structured database, initial vector-store direction, exact retrieval, orchestration, and initial reranker decision are sufficiently resolved. Live xAI generation behavior, JJM-specific embedding quality, pgvector performance, traffic/capacity, and deployment/security decisions remain legitimately unresolved and have explicit next benchmarks or external decisions.
