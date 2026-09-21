# Grok Generation Benchmark

## Result

`BLOCKED_BY_MISSING_XAI_API_KEY`

No `XAI_API_KEY` was present. No xAI request was made, no source data was sent, and no generation result is claimed. The machine-readable record is [artifacts/grok_generation_benchmark.json](../artifacts/grok_generation_benchmark.json).

## Controlled test set

The planned benchmark contains:

- Q002 policy question;
- Q003 exact lookup;
- Q009 structured numeric question;
- Q036 cross-document comparison;
- Q021 version-sensitive question;
- a synthetic insufficient-evidence question;
- Q014 provenance/citation question;
- Q039 multi-part hybrid question.

Each request will contain only the minimum retrieved evidence package, including source hashes, source status, report family, scope, date/period, table/row/column or page provenance, raw/normalized values, and uncertainty markers.

## Measurements

Grounding, numeric fidelity, scope fidelity, abstention, citation fidelity, structured-output validity, unsupported-fact rate, latency, token counts, and calculated cost must be recorded per case. This experiment must not be described as RAG accuracy; it evaluates answer generation over supplied evidence.

## Security boundary

Before running, confirm data-transfer approval, endpoint/region, retention behavior, token budget, timeout policy, and secret-management controls. Never send the complete corpus or print the API key.

## Decision

xAI Grok 4.6 remains the required preferred candidate, but the answer-generation decision is `REQUIRES_BENCHMARK`.
