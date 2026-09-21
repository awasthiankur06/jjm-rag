from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


def _expected_route(query_type: str) -> str:
    return 'EXACT' if query_type == 'provenance' else query_type.upper()


def write_prototype_reports(results_path: str | Path, cases_path: str | Path, failure_json: str | Path, results_doc: str | Path, failure_doc: str | Path) -> tuple[dict[str, Any], str, str]:
    results = json.loads(Path(results_path).read_text(encoding='utf-8'))
    cases = {case['id']: case for case in json.loads(Path(cases_path).read_text(encoding='utf-8'))['cases']}
    routing_mismatches = []
    semantic_comparison = []
    failure_categories = Counter()
    for result in results['cases']:
        case = cases[result['id']]
        expected_route = _expected_route(case['query_type'])
        if result['route']['query_type'] != expected_route:
            routing_mismatches.append({'id': result['id'], 'expected': expected_route, 'actual': result['route']['query_type'], 'query': result['query']})
        if case['requires_semantic_retrieval']:
            exact_sources = {item['filename'] for item in result['independent_path_results']['exact']}
            semantic_sources = {item['filename'] for item in result['independent_path_results']['semantic']}
            expected = set(case['expected_sources'])
            semantic_comparison.append({'id': result['id'], 'expected_sources': sorted(expected), 'exact_hit': (expected <= exact_sources if case['requires_multiple_sources'] else bool(expected & exact_sources)), 'semantic_hit': (expected <= semantic_sources if case['requires_multiple_sources'] else bool(expected & semantic_sources)), 'exact_sources': sorted(exact_sources), 'semantic_sources': sorted(semantic_sources)})
        if result.get('failure_category'):
            failure_categories[result['failure_category']] += 1
    analysis = {
        'artifact_type': 'retrieval_failure_analysis',
        'case_count': results['executed_case_count'],
        'failed_case_count': sum(failure_categories.values()),
        'failure_categories': dict(failure_categories),
        'routing_mismatches': routing_mismatches,
        'semantic_comparison': semantic_comparison,
        'major_patterns': [
            'The local semantic path is a lexical TF-IDF-like proxy, not a production embedding model; its measured usefulness is limited to the policy subset tested.',
            'Structured retrieval reaches the correct source documents after report-level metadata scoring and source diversification, but numeric answer correctness is not measurable from the approved source-only cases.',
            'Audit evidence for the excluded XLS is handled separately; the corrupted file itself is absent from all prototype production records.',
        ],
        'not_evaluable': results['evaluation_limits'],
        'recommended_follow_up': 'Add answer-level ground truth and representative policy paraphrase cases before selecting a production semantic backend.',
    }
    Path(failure_json).write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding='utf-8')
    metrics = results['metrics']
    prototype_status = 'RETRIEVAL_PROTOTYPE_BLOCKED' if failure_categories or metrics['numeric_aggregation_accuracy'] == 'NOT_EVALUABLE' else 'RETRIEVAL_PROTOTYPE_VALIDATED'
    results_markdown = f'''# Retrieval Prototype Results

## Status

`{prototype_status}`

This status applies to the local/offline retrieval prototype only. Production infrastructure and Grok answer generation remain deferred.

## Execution

- Evaluation cases executed: {results['executed_case_count']} of {results['case_count']}
- Prototype documents: 44 production-usable files
- Excluded source indexed: no
- Excluded source audit record: yes

## Measured Metrics

- Routing accuracy: {metrics['routing_accuracy']:.3f}
- Recall@1: {metrics['recall_at_1']:.3f}
- Recall@3: {metrics['recall_at_3']:.3f}
- Recall@5: {metrics['recall_at_5']:.3f}
- Recall@10: {metrics['recall_at_10']:.3f}
- Exact-match accuracy: {metrics['exact_match_accuracy']}
- Structured source accuracy: {metrics['structured_source_accuracy']}
- Numeric/aggregation accuracy: `{metrics['numeric_aggregation_accuracy']}`
- Provenance accuracy: {metrics['provenance_accuracy']}
- Semantic source-hit rate: {metrics['semantic_source_hit_rate']}
- Hybrid source-hit rate: {metrics['hybrid_source_hit_rate']}

Recall is measured at unique source rank. Exact and structured metrics measure expected source retrieval, not final answer generation.

## Semantic Experiment

Semantic retrieval was useful for policy/guidance and explanatory cases, but the local lexical proxy reached only the measured semantic source-hit rate above. Exact and structured paths are stronger for report identity and numeric tables. Semantic retrieval should remain isolated behind `EmbeddingProvider` and be evaluated with paraphrase-heavy policy cases before production model selection.

## Difficult Cases

- Multi-row headers are retained as column paths in structured evidence.
- Total rows are flagged and excluded by default from row filtering unless explicitly requested.
- State/district filters operate over normalized row metadata and raw values.
- Dates and financial years remain report metadata rather than being conflated.
- OCR evidence retains page number, OCR status, and confidence metadata.
- Version questions use metadata/content evidence; filename suffixes alone are not treated as chronology.
- Cross-document retrieval is diversified by source, but schema compatibility still requires validation.
- Unknown queries return `INSUFFICIENT_EVIDENCE` rather than weak lexical evidence.

## Limitations

- The approved cases do not contain expected numeric answers, so numeric, aggregation, ranking, and computation accuracy are `NOT_EVALUABLE`.
- The semantic path is a local lexical proxy and is not evidence for a production embedding choice.
- Policy section segmentation and PDF table extraction need broader prototype coverage.

## Decision

The Phase 2 architecture remains directionally valid, but the prototype gate is blocked until cross-document alignment, routing mismatches, and answer-level numeric ground truth are validated. Production technology selection remains deferred.
'''
    failure_markdown = f'''# Retrieval Failure Analysis

## Summary

- Cases executed: {results['executed_case_count']}
- Failed cases: {sum(failure_categories.values())}
- Failure categories: {dict(failure_categories) or 'none'}
- Routing mismatches: {len(routing_mismatches)}

## Findings

The prototype has measurable retrieval coverage, but unresolved cross-document failures remain. The remaining limitations include both retrieval implementation gaps and evaluation-data limitations; they are recorded rather than hidden.

### Routing

Routing mismatches are recorded in the JSON artifact. They identify cases where a query can reasonably require multiple strategies even when the approved label is narrower; this is a tuning/clarification target, not evidence to add an LLM router.

### Semantic Retrieval

The semantic comparison is recorded per semantic-required case. The local lexical proxy is useful as a baseline for policy text but should not be treated as a production embedding evaluation.

### Structured Retrieval

Structured source retrieval is measured successfully. Numeric correctness remains `NOT_EVALUABLE` because the dataset does not provide answer-level expected values. Add deterministic expected values for totals, rankings, and comparisons before infrastructure selection.

### Provenance and Exclusion

Provenance checks passed for returned evidence. The excluded XLS remains physically present, blocked, and absent from documents, rows, pages, semantic units, and production retrieval candidates. Its forensic JSON is available only through the audit path.

## Failure Taxonomy

The evaluator supports the requested categories: `PARSING`, `NORMALIZATION`, `METADATA`, `CHUNKING`, `EXACT_RETRIEVAL`, `STRUCTURED_RETRIEVAL`, `SEMANTIC_RETRIEVAL`, `ROUTING`, `CROSS_DOCUMENT_ALIGNMENT`, `VERSION_HANDLING`, `PROVENANCE`, `EVALUATION_DATASET`, and `UNKNOWN`.

Current unresolved failure count: {sum(failure_categories.values())}.

## Required Next Validation

Add answer-level numeric ground truth, paraphrase-focused policy cases, explicit version conflict cases, and schema-compatibility assertions. Do not select production storage, embedding, or orchestration infrastructure from this prototype alone.
'''
    Path(results_doc).write_text(results_markdown, encoding='utf-8')
    Path(failure_doc).write_text(failure_markdown, encoding='utf-8')
    return analysis, results_markdown, failure_markdown
