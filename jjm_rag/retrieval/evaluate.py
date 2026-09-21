from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from jjm_rag.retrieval.prototype import EXCLUDED_FILENAME, PrototypeRetriever

FAILURE_CATEGORIES = {
    'PARSING', 'NORMALIZATION', 'METADATA', 'CHUNKING', 'EXACT_RETRIEVAL',
    'STRUCTURED_RETRIEVAL', 'SEMANTIC_RETRIEVAL', 'ROUTING',
    'CROSS_DOCUMENT_ALIGNMENT', 'VERSION_HANDLING', 'PROVENANCE',
    'EVALUATION_DATASET', 'UNKNOWN',
}


def source_names(evidence: list[dict[str, Any]]) -> set[str]:
    return {item['filename'] for item in evidence}


def expected_sources(case: dict[str, Any]) -> set[str]:
    return set(case['expected_sources'])


def production_expected_sources(case: dict[str, Any]) -> set[str]:
    return {
        source for source in expected_sources(case)
        if source != EXCLUDED_FILENAME and not source.startswith('artifacts/')
    }


def audit_evidence_available(case: dict[str, Any], root: Path) -> bool:
    audit_sources = [source for source in case['expected_sources'] if source.startswith('artifacts/')]
    if not audit_sources:
        return True
    return all((root / source).exists() for source in audit_sources)


def hit_fraction(expected: set[str], actual: set[str]) -> float:
    return len(expected & actual) / len(expected) if expected else 0.0


def sources_satisfy(case: dict[str, Any], expected: set[str], actual: set[str]) -> bool:
    if not expected:
        return True
    return expected <= actual if case['requires_multiple_sources'] else bool(expected & actual)


def unique_sources_at(evidence: list[dict[str, Any]], limit: int) -> set[str]:
    """Measure source recall at unique-source rank, not repeated row rank."""
    result = []
    for item in evidence:
        filename = item['filename']
        if filename not in result:
            result.append(filename)
        if len(result) >= limit:
            break
    return set(result)


def provenance_valid(evidence: list[dict[str, Any]]) -> bool:
    return bool(evidence) and all(item.get('filename') and isinstance(item.get('location'), dict) for item in evidence)


def infer_failure(case: dict[str, Any], result: dict[str, Any], expected_hit: bool) -> str | None:
    if expected_hit:
        return None
    if not result['evidence']:
        if case['query_type'] == 'policy':
            return 'SEMANTIC_RETRIEVAL'
        if case['query_type'] in {'structured', 'cross_document'}:
            return 'STRUCTURED_RETRIEVAL'
        return 'EXACT_RETRIEVAL'
    if case['query_type'] == 'version':
        return 'VERSION_HANDLING'
    if case['query_type'] == 'cross_document':
        return 'CROSS_DOCUMENT_ALIGNMENT'
    if case['query_type'] == 'policy':
        return 'SEMANTIC_RETRIEVAL'
    if case['query_type'] == 'structured':
        return 'STRUCTURED_RETRIEVAL'
    return 'EXACT_RETRIEVAL'


def evaluate_cases(artifact: dict[str, Any], cases: list[dict[str, Any]], artifact_root: Path | None = None, retriever_factory=None) -> dict[str, Any]:
    retriever = retriever_factory(artifact) if retriever_factory else PrototypeRetriever(artifact)
    per_case = []
    routing_hits = 0
    exact_cases = 0
    exact_hits = 0
    structured_cases = 0
    structured_hits = 0
    provenance_cases = 0
    provenance_hits = 0
    cross_document_cases = 0
    cross_document_hits = 0
    strategy_hits = Counter()
    failure_categories = Counter()
    recall_sums = {1: 0.0, 3: 0.0, 5: 0.0, 10: 0.0}
    recall_counts = {1: 0, 3: 0, 5: 0, 10: 0}

    for case in cases:
        query = case['query']
        routed = retriever.retrieve(query, top_k=10)
        exact = retriever.exact.search(query, top_k=10)
        structured = retriever.structured.search(query, routed['route'].get('filters', {}), top_k=10)
        semantic = retriever.semantic.search(query, top_k=10)
        production_expected = production_expected_sources(case)
        audit_expected = {source for source in expected_sources(case) if source.startswith('artifacts/')}
        actual = source_names(routed['evidence'])
        exact_sources = source_names([item.__dict__ for item in exact])
        audit_hit = audit_evidence_available(case, artifact_root or Path('.')) and audit_expected <= exact_sources
        source_hit = (
            (not production_expected or (production_expected <= actual if case['requires_multiple_sources'] else bool(production_expected & actual)))
            and (not audit_expected or audit_hit)
        )
        expected_route = case['query_type'].upper()
        if expected_route == 'PROVENANCE':
            expected_route = 'EXACT'
        route_hit = routed['route']['query_type'] == expected_route
        if route_hit:
            routing_hits += 1
        if case['requires_exact_match'] and not audit_expected:
            exact_cases += 1
            if sources_satisfy(case, production_expected, source_names([item.__dict__ for item in exact])):
                exact_hits += 1
        if case['requires_structured_query']:
            structured_cases += 1
            if sources_satisfy(case, production_expected, source_names([item.__dict__ for item in structured])):
                structured_hits += 1
        if case['requires_provenance']:
            provenance_cases += 1
            if (audit_expected and audit_hit) or (not audit_expected and provenance_valid(routed['evidence'])):
                provenance_hits += 1
        for k in recall_sums:
            top_sources = unique_sources_at(routed['evidence'], k)
            if production_expected:
                recall_sums[k] += hit_fraction(production_expected, top_sources)
                recall_counts[k] += 1
        strategy_hits[routed['route']['query_type']] += int(source_hit)
        if case['query_type'] == 'cross_document':
            cross_document_cases += 1
            cross_document_hits += int(source_hit)
        failure = infer_failure(case, routed, source_hit)
        if failure:
            failure_categories[failure] += 1
        per_case.append({
            'id': case['id'],
            'query': query,
            'expected_sources': sorted(expected_sources(case)),
            'actual_sources': sorted(actual),
            'audit_evidence_available': audit_hit if audit_expected else 'NOT_EVALUABLE',
            'route': routed['route'],
            'selected_strategies': routed['strategies'],
            'top_k_results': routed['evidence'],
            'independent_path_results': {
                'exact': [item.__dict__ for item in exact[:10]],
                'structured': [item.__dict__ for item in structured[:10]],
                'semantic': [item.__dict__ for item in semantic[:10]],
            },
            'expected_evidence_retrieved': source_hit,
            'provenance_correct': ((audit_expected and audit_hit) or (not audit_expected and provenance_valid(routed['evidence']))) if case['requires_provenance'] else 'NOT_EVALUABLE',
            'structured_result_correct': 'NOT_EVALUABLE',
            'numeric_result_correct': 'NOT_EVALUABLE',
            'exact_match_success': ((production_expected <= exact_sources) if case['requires_exact_match'] and case['requires_multiple_sources'] and not audit_expected else (bool(production_expected & exact_sources) if case['requires_exact_match'] and not audit_expected else 'NOT_EVALUABLE')),
            'semantic_source_hit': sources_satisfy(case, production_expected, source_names([item.__dict__ for item in semantic])) if case['requires_semantic_retrieval'] else 'NOT_EVALUABLE',
            'failure_category': failure,
            'failure_reason': 'Expected source was not retrieved in top 10.' if failure else None,
        })

    semantic_cases = [item for item in per_case if item['semantic_source_hit'] != 'NOT_EVALUABLE']
    semantic_hits = sum(item['semantic_source_hit'] for item in semantic_cases)
    hybrid_cases = [item for item in per_case if item['route']['query_type'] == 'HYBRID']
    hybrid_hits = sum(item['expected_evidence_retrieved'] for item in hybrid_cases)
    return {
        'artifact_type': 'local_retrieval_prototype_evaluation',
        'case_count': len(cases),
        'executed_case_count': len(per_case),
        'metrics': {
            'routing_accuracy': routing_hits / len(cases) if cases else 0,
            'recall_at_1': recall_sums[1] / recall_counts[1] if recall_counts[1] else 0,
            'recall_at_3': recall_sums[3] / recall_counts[3] if recall_counts[3] else 0,
            'recall_at_5': recall_sums[5] / recall_counts[5] if recall_counts[5] else 0,
            'recall_at_10': recall_sums[10] / recall_counts[10] if recall_counts[10] else 0,
            'exact_match_accuracy': exact_hits / exact_cases if exact_cases else 'NOT_EVALUABLE',
            'structured_source_accuracy': structured_hits / structured_cases if structured_cases else 'NOT_EVALUABLE',
            'exact_retrieval_accuracy': exact_hits / exact_cases if exact_cases else 'NOT_EVALUABLE',
            'structured_retrieval_accuracy': structured_hits / structured_cases if structured_cases else 'NOT_EVALUABLE',
            'numeric_aggregation_accuracy': 'NOT_EVALUABLE',
            'provenance_accuracy': provenance_hits / provenance_cases if provenance_cases else 'NOT_EVALUABLE',
            'semantic_source_hit_rate': semantic_hits / len(semantic_cases) if semantic_cases else 'NOT_EVALUABLE',
            'semantic_retrieval_accuracy': semantic_hits / len(semantic_cases) if semantic_cases else 'NOT_EVALUABLE',
            'hybrid_source_hit_rate': hybrid_hits / len(hybrid_cases) if hybrid_cases else 'NOT_EVALUABLE',
            'hybrid_retrieval_accuracy': hybrid_hits / len(hybrid_cases) if hybrid_cases else 'NOT_EVALUABLE',
            'cross_document_accuracy': cross_document_hits / cross_document_cases if cross_document_cases else 'NOT_EVALUABLE',
        },
        'strategy_hit_counts': dict(strategy_hits),
        'failure_categories': dict(failure_categories),
        'cases': per_case,
        'evaluation_limits': [
            'The approved cases specify expected source files but do not provide answer-level numeric ground truth for every aggregation.',
            'Numeric, aggregation, and ranking correctness are therefore NOT_EVALUABLE unless independently derived expected values are added.',
            'The semantic path is a local lexical TF-IDF-like proxy, not a production embedding model.',
        ],
    }


def run_evaluation(manifest_path: str | Path, cases_path: str | Path, prototype_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    artifact = json.loads(Path(prototype_path).read_text(encoding='utf-8'))
    cases = json.loads(Path(cases_path).read_text(encoding='utf-8'))['cases']
    result = evaluate_cases(artifact, cases, Path(output_path).parent.parent)
    result['corpus_manifest'] = str(manifest_path)
    Path(output_path).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    return result
