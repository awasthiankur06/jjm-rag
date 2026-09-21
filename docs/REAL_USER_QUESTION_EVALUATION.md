# Real User Question Evaluation

Executed **40** realistic JJM questions through the existing FastAPI `/api/v1/query` and `RagService` path.

## Distribution

- policy_guideline: 8
- report_fact: 9
- exact_numeric: 3
- state_level: 2
- district_level: 1
- comparison: 4
- aggregation: 3
- cross_document: 3
- reporting_period: 4
- unsupported_abstention: 3

## Metrics

- routing_accuracy: 0.975
- recall_at_1: NOT_EVALUABLE_FROM_RESPONSE_ONLY
- recall_at_3: NOT_EVALUABLE_FROM_RESPONSE_ONLY
- recall_at_5: NOT_EVALUABLE_FROM_RESPONSE_ONLY
- recall_at_10: 0.85
- grounded_answer_rate: 0.525
- correct_answer_rate: NOT_EVALUABLE_FOR_QUALITATIVE_CASES
- numeric_accuracy: 0.8
- geographic_accuracy: NOT_EVALUABLE_WITHOUT_ANSWER_LEVEL_GEOGRAPHY_JUDGER
- citation_provenance_accuracy: 1.0
- citation_source_accuracy: 1.0
- cross_document_success: 0.3333333333333333
- abstention_correctness: 1.0
- calculation_retrieval_correct: 1.0
- calculation_correct: 0.25
- calculation_final_answer_correct: NOT_EVALUABLE_WHERE_EXPECTED_RESULT_IS_DERIVED

## Failure categories

- grounding_failure: 9
- numeric_extraction_failure: 1
- retrieval_failure: 4
- wrong_routing: 1
- cross_document_alignment_failure: 2

## Interpretation

This is a measured production-path baseline. Numeric and calculation rates are intentionally marked unevaluable where answer-level ground truth was not independently derived from structured records. The current API returns retrieved evidence and Grok output but does not expose a deterministic structured calculation service; that is the main next engineering gap.
