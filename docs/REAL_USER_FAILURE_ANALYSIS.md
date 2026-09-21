# Real User Failure Analysis

## Scope

This is a read-only diagnosis of the 40-question production-path evaluation in [real_user_question_evaluation_results.json](../artifacts/real_user_question_evaluation_results.json). No retrieval, RAG, Grok, PostgreSQL, Qdrant, Gemini, corpus, or benchmark changes were made.

The captured evaluation stores retrieved filenames, citations, answers, grounding, route, and aggregate response metadata. It does not store the complete evidence packet sent to Grok. Therefore, this report distinguishes:

- **Captured retrieval evidence**: expected source family appears in the recorded response.
- **Authoritative data evidence**: PostgreSQL spot checks confirm a matching structured observation exists.
- **Unknown boundary**: the artifact cannot prove whether the full structured observation was actually included in the Grok context.

## Headline Finding

The main problem is not simply vector retrieval.

Of 30 failed cases:

- 17 retrieved the expected source family.
- 13 did not retrieve the expected source family.
- 15 had expected sources present but still returned an ungrounded/abstaining answer.
- 2 were grounded but still failed their evaluated requirement.
- 28 failed cases returned zero citations despite nonzero evidence counts.

PostgreSQL contains exact structured observations for the central numeric failures, including:

- Khammam/Telangana: 107304 house connections, 100.00% FHTC coverage, 270254 total households on 15/08/2019.
- Thrissur/Kerala: 614994 total households and 50.15% FHTC coverage on 15/08/2019.
- Balaghat/Madhya Pradesh: 368267 total households, 365995 later house connections, and 99.38% FHTC coverage.
- Champawat: 196355 rural population on 01/04/2026.

The current production path does not expose these as a typed fact packet. It returns generic `Evidence` text and metadata, then asks Grok to identify values, periods, and arithmetic. That is the primary answer-layer gap.

## Failure Distribution

| Primary stage | Cases |
|---|---:|
| Retrieval | 6 |
| Geography | 3 |
| Routing | 3 |
| Structured fact handling | 6 |
| Evidence construction | 2 |
| Calculation | 2 |
| Numeric extraction | 1 |
| Grounding policy | 1 |
| Reporting period/version | 4 |
| Cross-document | 2 |
| **Total** | **30** |

The original evaluator labels remain preserved in the artifact. The table above is a diagnostic reassignment to the earliest controlling stage, not a rewrite of the original evaluation.

## Case-Level Diagnosis

The full structured case records are in [real_user_failure_analysis.json](../artifacts/real_user_failure_analysis.json). The most important patterns are:

### Structured numeric cases

`RU009`, `RU010`, `RU011`, `RU012`, `RU016`, and `RU017` retrieved the expected report families, but Grok received no usable answer-level fact result and the service abstained. Direct PostgreSQL inspection confirms exact observations for the Khammam, Thrissur, and Balaghat cases. These are structured-fact/evidence-construction failures, not proof of missing corpus data.

`RU030` retrieved and grounded the policy side of a cross-document question, but omitted the Khammam numeric observation. PostgreSQL confirms the expected `107304` value. This is numeric extraction/context use, not citation validation.

### Geography

`RU013`–`RU015` failed to return the requested Assam, Uttar Pradesh, and Champawat population facts. The database contains geography-linked records for the relevant data families, including Champawat with `196355` and `01/04/2026`. The current structured query uses broad token matching and does not reliably bind metric, state/district, and snapshot together. These are geography/filter selection failures.

### Calculations

`RU021`, `RU026`, and `RU027` require comparing or calculating from multiple structured operands. The evaluation measured calculation retrieval at 75% but calculation correctness at 0%. No deterministic calculation boundary exists. Grok is responsible for both selecting operands and doing arithmetic, which is the wrong ownership boundary for exact JJM numbers.

### Reporting periods and versions

The schema has `report_date`, `reporting_period`, `financial_year`, and `snapshot_label`, but they are nullable text fields. `document_versions` tracks content identity and hashes, while `version_evidence`/`version_confidence` can remain insufficient/unknown. There is no reliable latest-snapshot ordering contract. Filename suffixes are explicitly not chronology. `RU022`, `RU031`, `RU032`, `RU033`, and `RU037` expose this gap.

### Cross-document

`RU028` did not retrieve both expected source groups. `RU029` recorded both guideline and progress-tracker families, but still abstained without citations. This shows two separate problems: multi-source retrieval coverage and preservation/alignment of source groups through context construction. A flat fused top-k list does not guarantee that each required document family survives.

### Grounding

The grounding validator correctly rejects answers without valid citation markers, but grounding is coupled to free-form Grok output. When structured facts are not exposed in context, abstention is safe but not diagnostically specific. The system cannot currently distinguish “fact absent from retrieved context” from “fact present but Grok failed to use it” because the evaluation artifact lacks the full evidence packet and the response lacks typed fact support metadata.

## Data Model Assessment

The existing schema already stores the essential atomic fields:

- `structured_records.metric_name`
- `structured_records.value_raw`
- `structured_records.value_numeric`
- `structured_records.unit`
- `geography_dimensions.state_name`
- `geography_dimensions.district_name`
- `reporting_dimensions.report_date`
- `reporting_dimensions.reporting_period`
- `reporting_dimensions.financial_year`
- `documents.filename/document_id`
- `provenance_records` and `structured_records.provenance_id`

The gap is primarily the production query contract and selection semantics, not lack of storage. Current `PostgresEvidenceStore.structured()` returns rows, but its predicate is broad text matching over report/metric/value/content fields, and its returned evidence string is only `metric_name: value_raw`. It does not reliably expose the complete metric, geography, period, unit, document, and provenance tuple as a first-class answer object.

## Recommended Smallest General Solution

```text
User question
  -> classify and normalize intent
  -> policy/explanatory: semantic + lexical evidence
  -> exact fact: structured + exact/lexical
  -> numeric fact: typed structured observations
  -> calculation: typed observations -> deterministic calculation
  -> period/version: explicit reporting metadata and validated ordering
  -> cross-document: required source groups retrieved independently
  -> evidence validation
  -> context construction with typed fact packets
  -> Grok explains validated facts and calculations
  -> citation and grounding validation
```

The smallest general implementation should reuse the existing schema and service boundaries:

1. Add a typed structured-fact result contract to the existing PostgreSQL adapter. It should preserve metric, raw/numeric value, unit, state, district, report date/period, document, record ID, and provenance.
2. Add deterministic calculation orchestration for sum, difference, average, percentage-of-total, and maximum only after all operands pass identity and period validation.
3. Add explicit geography and reporting filters rather than broad token matching. Keep geography fields separate from metric/value text.
4. Preserve source groups for cross-document questions and require each requested group before generation.
5. Validate grounding against typed fact support and provenance, not only `[n]` markers in a free-form answer.
6. Extend the evaluation capture to retain the full evidence packet and typed observations so future failures can be assigned confidently to retrieval versus answer-layer stages.

## Priority Order

1. Typed structured-fact retrieval contract.
2. Deterministic calculation boundary.
3. Geography and reporting-period filtering/normalization.
4. Multi-source evidence-group preservation.
5. Grounding validation against typed support.
6. Re-run the same 40-question evaluation and compare metrics.

## Status

`ANALYSIS_ONLY_NO_FIXES_IMPLEMENTED`

No index, corpus, protected artifact, retrieval implementation, generation implementation, API behavior, or evaluation questions were changed.
