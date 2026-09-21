# Ingestion Validation Report
- filesystem_count: 45
- physical_corpus_count: 45
- production_usable_count: 44
- excluded_count: 1
- production_ingestion_counts: {'included': 44, 'excluded': 1}
- quality_counts: {'PASS': 43, 'PASS_WITH_WARNINGS': 1, 'BLOCKED': 1}
- phase_1_gate: PASS_WITH_EXCLUDED_SOURCE
- phase_1_blockers: none
- files summary:
  - html: 42
  - pdf: 3

## Files needing attention
- Operational-Guidelines-JJM-2.pdf: OCR coverage=100.0%; success=200; failed=0; near_empty=13; confidence_mean=83.20189081319154
- Status of Pipe Water Supply in School (2).xls: TRUNCATED_OR_CORRUPTED; production_decision=EXCLUDED_CORRUPTED_SOURCE; unchanged; no repair or inference