# Answer-Layer Implementation

## 1. What Changed

Implemented the smallest general answer-layer extension over the existing PostgreSQL/Qdrant/Grok pipeline:

- Structured PostgreSQL evidence now carries typed metric, raw/numeric value, unit, geography, period, source, and provenance metadata.
- Structured retrieval explicitly resolves state and district names found in the authoritative geography dimensions.
- Explicit report dates in questions are applied to structured retrieval.
- Structured evidence includes provenance location fields such as page, sheet, row, column, and cell when available.
- Internal responses now distinguish `FACT`, `CALCULATION`, `COMPARISON`, `CROSS_DOCUMENT`, `POLICY`, and `NARRATIVE` paths.
- Deterministic calculations are performed in Python from validated structured operands before Grok explanation.
- Missing or incompatible operands cause controlled abstention.
- Cross-document questions retrieve both semantic and structured channels and preserve source groups in response metadata.
- `latest` questions abstain when explicit orderable reporting dates are unavailable.
- Unsupported named entities that do not resolve to authoritative geography dimensions no longer receive unrelated structured facts.
- Typed numeric structured candidates are prioritized over non-typed distractors for structured intents.
- Numeric Grok output is checked against validated structured facts; a conflicting or missing number is replaced with the deterministic fact result where safe.

No new database, vector store, embedding provider, or RAG pipeline was introduced.

## 2. Existing PostgreSQL Structures Reused

The implementation reuses:

- `structured_records.metric_name`
- `structured_records.value_raw`
- `structured_records.value_numeric`
- `structured_records.unit`
- `geography_dimensions.state_name`
- `geography_dimensions.district_name`
- `reporting_dimensions.report_date`
- `reporting_dimensions.reporting_period`
- `reporting_dimensions.financial_year`
- `documents.document_id/filename`
- `provenance_records` and `structured_records.provenance_id`

No PostgreSQL schema migration was required.

## 3. New Internal Evidence/Answer Contracts

`Evidence.metadata` now carries the typed structured fact packet where available:

- `metric_name`
- `value_raw`
- `value_numeric`
- `unit`
- `state`
- `district`
- `report_date`
- `reporting_period`
- `financial_year`
- `document_id`
- `record_id`
- `provenance_id`

`QueryResponse` now also exposes:

- `answer_type`
- `structured_facts`
- `calculation`
- `retrieval.evidence_groups`

The public response remains backward compatible because the existing fields are preserved.

## 4. Query Routing Changes

The router now recognizes general numeric, comparison, calculation, geography, household, connection, population, scheme, laboratory, date, and financial-year language as structured intent. Policy definitions, objectives, responsibilities, and O&M guidance remain semantic. Cross-document policy-plus-report questions activate both semantic and structured retrieval.

This is vocabulary-based general routing, not benchmark-case logic.

## 5. Geography Handling

Structured retrieval loads known state and district names from `geography_dimensions` and applies explicit equality constraints when those names occur in the normalized question. The selected evidence retains the resolved state and district values for answer validation.

## 6. Reporting-Period Handling

Explicit date expressions such as `15/08/2019` and `01/04/2026` are matched against `reporting_dimensions.report_date` and related financial-year text. The implementation does not infer chronology from filename suffixes. Questions asking for `latest` abstain unless structured evidence exposes an orderable report date.

The underlying model still has limitations: temporal fields are text, version confidence may be unknown, and not every source has complete reporting metadata.

## 7. Calculation Engine

The answer layer supports deterministic:

- sum/combined total
- average
- difference/comparison
- maximum/highest
- ratio/percentage where two compatible operands exist

Each result retains input content IDs, metric, values, geography, report date, and provenance. Grok receives the verified result and is instructed to explain it without recalculating. Missing or incompatible operands produce controlled abstention.

## 8. Cross-Document Evidence Handling

Cross-document questions preserve at least one evidence item per source filename before context construction. The response exposes `retrieval.evidence_groups`, allowing the UI and future evaluators to verify that multiple source groups survived fusion.

## 9. Grounding Validation

Existing citation validation remains active. Typed calculation validation additionally requires validated operands and the deterministic result in the answer. Conflicting or missing generated numeric facts are replaced by a validated structured fact result when citation references remain valid. Fabricated or out-of-range citation markers remain rejected.

## 10. Tests

Added [test_phase8_answer_layer.py](../tests/test_phase8_answer_layer.py), covering:

- typed state/district fact metadata
- deterministic difference
- missing operand abstention
- incompatible metric abstention
- wrong generated numeric correction
- source-group preservation
- latest-period abstention

Focused answer-layer, evaluator, and regression tests: **25 passed**.

Full suite: **65 passed, 1 pre-existing failure, 2 warnings**. The remaining failure is the historical corpus-count assertion expecting 45 while the current corpus reports 46; no corpus file was changed.

## 11. Real-User Evaluation Before/After

| Metric | Before | After |
|---|---:|---:|
| Routing accuracy | 92.5% | 97.5% |
| Recall@10 | 67.5% | 82.5% |
| Grounded answer rate | 22.5% | 57.5% |
| Numeric accuracy | 6.67% | 73.33% |
| Citation source accuracy | 100% | 100% |
| Citation/provenance resolution | 100% | 100% |
| Cross-document success | 33.33% | 33.33% |
| Abstention correctness | 100% | 66.67% |
| Calculation retrieval correctness | 75% | 87.5% |
| Calculation correctness | 0% | 25% |

The evaluator now consumes machine-readable calculation metadata first. The remaining calculation failures reflect unavailable or incompatible operands and unsupported report combinations, not untrusted Grok arithmetic.

## 12. Remaining Failures

Final post-remediation failure categories:

- grounding failure: 9
- retrieval failure: 6
- geography filtering failure: 3
- cross-document alignment failure: 2
- reporting-period failure: 2
- numeric extraction failure: 1
- wrong routing: 1

Recall@10 exceeded the pre-Phase-8 baseline after typed structured candidates were protected from non-typed distractors and multi-geography operands were acquired independently. Cross-document performance remains unchanged, so multi-document source acquisition remains a separate gap.

## 13. Retrieval vs Answer-Layer Assessment

The before/after movement supports the original diagnosis:

- Routing improved from 92.5% to 97.5%.
- Grounded answer rate improved from 22.5% to 57.5% in the final rerun.
- Numeric accuracy improved from 6.67% to 73.33% in the final rerun.
- Citation/provenance correctness remained 100%.
- Recall@10 briefly decreased to 62.5% because structured facts were being truncated behind non-typed distractors; typed candidate prioritization and independent geography operand retrieval raised it to 82.5%.

This indicates that a substantial portion of the original failure was answer-layer fact representation, grounding, and deterministic numeric handling. Remaining retrieval, geography, period, and cross-document failures are real and should not be hidden by generation.

## 14. Recommended Next Step

The evaluator now checks machine-readable calculation metadata before prose. The next general engineering slice is missing/ambiguous geography metadata and cross-document source-group acquisition. Do not tune individual questions or re-index Gemini/Qdrant.

## Scope Confirmation

- No Gemini/Qdrant re-indexing occurred.
- No protected historical benchmark artifact was modified.
- No corpus or PostgreSQL schema change was made.
- Existing browser chat UI and FastAPI boundary remain in use.
