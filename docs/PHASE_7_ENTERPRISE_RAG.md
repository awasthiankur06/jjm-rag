# Phase 7 enterprise RAG

## Gate

`PHASE_7_ENTERPRISE_RAG_PARTIALLY_READY`

The production orchestration foundation is implemented with cloud-only AI boundaries. External embedding, vector, and xAI credentials/endpoints are not configured in this environment, so no paid cloud calls or production-quality claims are made.

## Architecture

PostgreSQL remains authoritative for documents, versions, structured observations, canonical content, geography, reporting, provenance, and ingestion audit. Cloud semantic infrastructure is an index/cache keyed by `content_unit_id` and points back to PostgreSQL evidence.

The service flow is:

```text
request validation
-> deterministic routing
-> exact / lexical / structured retrieval
-> optional cloud semantic retrieval
-> evidence filtering and deduplication
-> bounded context
-> optional xAI/Grok generation
-> citation and confidence response
```

Implemented modules:

- [jjm_rag/production/providers.py](../jjm_rag/production/providers.py): cloud embeddings and xAI adapters using bounded HTTP retries.
- [jjm_rag/production/vectorstore.py](../jjm_rag/production/vectorstore.py): provider-neutral managed vector adapter.
- [jjm_rag/production/postgres_store.py](../jjm_rag/production/postgres_store.py): parameterized exact, lexical, and structured evidence queries.
- [jjm_rag/production/rag.py](../jjm_rag/production/rag.py): routing, fusion, excluded-source filtering, grounding policy, citations, and confidence.
- [jjm_rag/production/api.py](../jjm_rag/production/api.py): optional FastAPI boundary.
- [jjm_rag/production/cli.py](../jjm_rag/production/cli.py): retrieval-only/cloud-configured CLI entry point.

## Cloud provider configuration

Configuration is environment-driven:

- `EMBEDDING_API_KEY`, `EMBEDDING_API_BASE`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`
- `VECTOR_API_KEY`, `VECTOR_API_BASE`, `VECTOR_INDEX`, `VECTOR_NAMESPACE`
- `XAI_API_KEY`, `XAI_BASE_URL`, `XAI_MODEL`

No credentials are stored in source, artifacts, documentation, tests, or logs. Local model inference is not used by the production path, even if development environments contain ML packages from earlier benchmark enablement.

## Retrieval rules

- Numeric, date, aggregation, and comparison facts come from PostgreSQL structured retrieval.
- Exact identifiers and filenames use exact retrieval.
- Lexical PostgreSQL retrieval handles phrases and terms.
- Semantic retrieval is optional and cloud-only.
- Missing semantic providers do not disable structured/exact/lexical retrieval.
- The excluded corrupted source is removed before evidence fusion and cannot be cited or sent to Grok.

## Grounding and citations

The generation prompt treats retrieved documents as data, not instructions. It requires evidence-only answers, no invented numbers, explicit insufficiency, and citation markers. Response citations resolve to returned evidence IDs and provenance metadata. Invalid or absent evidence produces a safe insufficient-evidence response.

## API

When FastAPI is installed, construct the boundary with `create_app(service)`:

- `GET /health`: process health.
- `GET /ready`: dependency configuration status; degraded when optional cloud providers are unavailable.
- `POST /api/v1/query`: bounded query request with query, filters, and options.

Business logic remains usable without FastAPI.

## CLI

```text
python -m jjm_rag.production.cli "How many districts are represented?" --retrieval-only
```

Cloud calls are not attempted unless provider configuration is complete.

## Security and resilience

- API keys are read only from environment variables.
- Provider timeouts and bounded exponential retry are implemented.
- Authentication and validation errors are not retried indefinitely.
- SQL values are parameterized.
- Query length and evidence count are bounded.
- Provider error messages do not include credentials or raw response bodies.
- Request IDs isolate response state.

## Validation status

Observed local validation:

- existing retrieval baseline remains protected;
- Phase 6B candidate policy remains 635 eligible units;
- cloud provider adapters and safe-degradation behavior are unit-testable;
- no cloud calls were executed without credentials.

Unavailable external validation:

- cloud embedding request and measured dimensions/latency;
- managed vector upsert/search;
- xAI/Grok generation;
- paid end-to-end smoke test.

## Dependencies

Only application boundary dependencies were added: FastAPI and Uvicorn. No local model runtime, vector database package, agent framework, or orchestration framework was added for Phase 7.

## Required next step

Configure approved cloud embedding, vector, and xAI providers in a controlled environment and run the explicit production smoke test. Do not claim `PHASE_7_ENTERPRISE_RAG_READY` until cloud semantic retrieval, Grok generation, citation validation, and end-to-end grounding are observed.
