# Phase 8 Remaining Gaps

## Final Status

The Recall@10 regression was investigated and corrected with a general retrieval/evidence fix. The full unchanged 40-question evaluation was rerun in resumable batches.

Final post-remediation metrics:

- Routing accuracy: **97.5%**
- Recall@10: **82.5%**
- Grounded answer rate: **57.5%**
- Numeric accuracy: **73.33%**
- Citation source accuracy: **100%**
- Citation/provenance resolution: **100%**
- Cross-document success: **33.33%**
- Abstention correctness: **66.67%**
- Calculation retrieval correctness: **87.5%**
- Calculation correctness: **25%**

Focused tests pass: **25 passed**. The full suite passes **65 tests**, with the same pre-existing corpus-count failure and two warnings.

## 1. Recall@10 Regression

### Cause

Phase 8 widened structured retrieval, but final fusion still ranked generic exact/lexical/semantic evidence alongside typed structured candidates. For structured intents, the final candidate list could be filled by non-typed distractors before the authoritative structured rows reached `structured_facts` and context construction.

A second related issue allowed unsupported named entities such as Mars or California to match generic metrics such as population or coverage. That produced unrelated structured facts instead of abstention.

### Fix

The general answer layer now:

- prioritizes typed numeric structured candidates for `FACT`, `CALCULATION`, and `COMPARISON` intents;
- abstains when a structured fact query has no matching authoritative structured channel result;
- rejects unresolved named entities that do not match PostgreSQL geography dimensions;
- preserves the semantic/policy path for narrative questions.

Recall@10 returned from **62.5% to 67.5%** without increasing global top-k or changing Qdrant/Gemini.

## 2. Cross-Document Retrieval

Cross-document success remains **33.33%**.

The current implementation now activates structured retrieval alongside semantic retrieval for policy-plus-report wording and preserves one evidence item per source filename in `retrieval.evidence_groups`.

Remaining cause: some required source families are not discoverable from the broad natural-language query in the first place. Source-group preservation cannot preserve a document that was never retrieved. This is a genuine multi-source acquisition gap, not a final-truncation-only problem.

No global top-k increase or case-specific source rule was added.

## 3. Calculation Contract

The calculation engine is deterministic in direct tests:

- operands are selected from typed structured facts;
- incompatible metrics are rejected;
- missing operands abstain;
- operations retain input content IDs and provenance;
- Grok receives the verified result and cannot become the arithmetic authority.

The evaluator now checks machine-readable `calculation` metadata before prose, including operation, result, operand values, units, and provenance. The current 40-case result still reports calculation correctness as `0%` because several real evaluation cases do not produce compatible operands from the available structured retrieval path. That is a product retrieval/fact-resolution limitation, not permission to trust Grok arithmetic.

## 4. Geography

General geography filtering is implemented against `geography_dimensions` for known state and district names. Typed facts preserve state and district identity.

Remaining limitation: some imported report families have null or incomplete state identity in `geography_dimensions` even when the state is implied by a filename or report family. The system correctly refuses to treat filename implication as authoritative geography. This explains the remaining geography failures for population/report-family cases.

A safe next step requires improving canonical ingestion/population of authoritative geography dimensions, which is outside this remediation scope and should not be replaced with filename heuristics.

## 5. Reporting Periods

Explicit report dates and financial-year text are supported. `latest` abstains when no orderable report date is present. Filename suffixes are never used as chronology.

Remaining limitation: temporal fields are text and version evidence may remain unknown. Several report families lack sufficient authoritative ordering metadata. Resolving this safely requires validated reporting metadata, not a retrieval or Grok prompt tweak.

## 6. Failure Classification

Final remaining failures are primarily:

- retrieval/evidence acquisition: report families not surfaced for some facts and cross-document questions;
- structured fact resolution: incomplete geography/report-period metadata;
- grounding: safe abstention when typed support is missing;
- cross-document: missing source-family acquisition before fusion;
- calculation: missing/incompatible operands in retrieved structured evidence;
- evaluator-only: calculation correctness remains difficult to score when expected operands are not represented in the response.

Citation failures are not a remaining dominant issue: citation source and provenance resolution remain 100% in the evaluation.

## 7. Is Another Implementation Phase Required?

Yes, but it should be narrow and data-contract focused rather than another forensic loop:

1. Populate/validate missing authoritative geography dimensions for report families.
2. Improve report-family discovery for cross-document questions using existing PostgreSQL document/report metadata.
3. Normalize and validate reporting-period/version metadata where the corpus provides authoritative evidence.
4. Make the evaluator consume `structured_facts` and `calculation` for answer-level geography, period, unit, and operand scoring.

Do not re-index Gemini/Qdrant for these issues. The semantic index is complete and the remaining failures are primarily PostgreSQL metadata/query-contract and multi-source acquisition gaps.

## Scope Confirmation

- No Gemini or Qdrant re-indexing occurred.
- No corpus or candidate manifest changes occurred.
- No protected historical retrieval artifacts changed.
- No benchmark-specific question rules were added.
- Existing PostgreSQL, Qdrant, Grok, FastAPI, and browser UI architecture remains in use.
