# Retrieval Architecture

## Status

`ARCHITECTURE_READY_FOR_PROTOTYPE`

This is a logical design only. No embeddings, vector indexes, framework integration, production APIs, or database ingestion have been implemented.

## Logical Pipeline

```text
User query
  |
  v
Query interpretation
  |-- identify intent: policy, exact, structured, hybrid, cross-document, version, provenance
  |-- extract entities: state, district, division, habitation, scheme, sanction, format, date
  |-- detect metrics, operators, comparison, and period constraints
  v
Evidence plan
  |-- policy branch: section/page semantic retrieval plus exact concept terms
  |-- exact branch: filename, format, identifier, entity, and raw-name lookup
  |-- structured branch: deterministic row/column/filter/aggregate execution
  |-- metadata branch: snapshot, hash, scope, source-status comparison
  |-- cross-document branch: aligned queries over common entity/metric/period keys
  v
Candidate evidence
  |-- exclude EXCLUDED_CORRUPTED_SOURCE records
  |-- enforce metadata filters and source-status rules
  |-- preserve table/header/row/page provenance
  v
Evidence validation
  |-- check numeric computations outside the LLM
  |-- detect conflicting snapshots or scopes
  |-- require sufficient evidence for every claim
  |-- return insufficiency or ambiguity when evidence is missing
  v
Evidence package
  |-- policy passages with document/page/section
  |-- structured results with report/table/row/column/value
  |-- exact matches with raw identifier and source hash
  |-- conflict and uncertainty annotations
  v
Grok/xAI synthesis (future phase)
  |
  v
Grounded answer with citations and limitations
```

## Routing Requirements

- Query routing is `RECOMMENDED`, not an implementation commitment to a framework. Numeric, exact, and policy requests have materially different evidence paths.
- Structured retrieval is mandatory for counts, totals, rankings, comparisons, and compound filters.
- Exact retrieval is mandatory for sanction numbers, format codes, filenames, state/district names, and source-status questions.
- Semantic retrieval is required for explanatory questions over guidance prose, but it is not sufficient for table arithmetic.
- Hybrid retrieval is required when a question combines a metric with policy meaning or joins a structured value to guidance.
- Version questions require metadata/content comparison before any semantic answer.

## Evidence and Safety Rules

1. Never retrieve or synthesize the excluded corrupted source as production content.
2. Keep raw source values beside normalized values.
3. Cite source filename, report/table, row/entity, column/metric, and page for PDFs.
4. State when reporting period is missing or sources conflict.
5. Prefer “the corpus does not contain sufficient evidence” over unsupported completion.
6. Keep deterministic aggregation, ranking, filtering, and comparison outside Grok.

## Future Grok Evidence Contract

The future synthesis layer should receive a typed evidence package, not an unlabelled text dump:

- `evidence_id`: stable request-local identifier
- `source_filename` and `sha256`: source identity
- `source_status` and `ingestion_status`: eligibility state
- `document_id`, `report_title`, `format_code`, and scope parameters
- `page` and `section` for PDFs; `table_id`, header path, row index, entity keys, and cell/column references for HTML reports
- `raw_value`, normalized value, unit, and any deterministic computation trace
- `extraction_warnings`, OCR confidence, and uncertainty labels

Citations should point to the smallest useful unit: PDF document/page/section, or report/table/row/column/cell for HTML exports. When two snapshots disagree, the answer must show both source identities and periods, avoid silently selecting one, and state that the values conflict. When a period, geography, or metric is missing, the system must ask for clarification or report insufficient evidence. When the only candidate is excluded or corrupted, it must not be passed as production evidence. Unsupported claims should be rejected in post-synthesis citation validation.

## Orchestration

A small deterministic router plus composable retrieval services is recommended for the prototype. A graph/orchestration framework is not yet justified because the workflow is not implemented and the required state transitions can be tested as plain functions first.
