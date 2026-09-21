import json
from pathlib import Path


ROOT = Path('d:/jjm-rag')


def load_cases():
    return json.loads((ROOT / 'artifacts/query_evaluation_cases.json').read_text(encoding='utf-8'))


def load_manifest():
    return json.loads((ROOT / 'artifacts/corpus_manifest_final.json').read_text(encoding='utf-8'))


def test_query_evaluation_cases_are_traceable_to_manifest():
    dataset = load_cases()
    manifest = load_manifest()
    filenames = {entry['filename'] for entry in manifest['files']}
    assert dataset['case_count'] == 40
    assert len(dataset['cases']) == 40
    for case in dataset['cases']:
        assert case['expected_sources']
        assert case['requires_provenance'] is True
        for source in case['expected_sources']:
            if source.startswith('artifacts/'):
                assert (ROOT / source).exists()
            else:
                assert source in filenames


def test_excluded_source_is_audit_only_in_phase2_dataset():
    dataset = load_cases()
    manifest = load_manifest()
    excluded = next(
        entry for entry in manifest['files']
        if entry['filename'] == 'Status of Pipe Water Supply in School (2).xls'
    )
    assert excluded['quality_state'] == 'BLOCKED'
    assert excluded['classification'] == 'TRUNCATED_OR_CORRUPTED'
    assert excluded['ingestion_status'] == 'EXCLUDED_CORRUPTED_SOURCE'
    assert excluded['sha256'] == 'bf4eafc15390dd98688a2f0306f28457a60bc027343e5346a0bc3be2d4009ee3'
    audit_cases = [
        case for case in dataset['cases']
        if excluded['filename'] in case['expected_sources']
    ]
    assert {case['id'] for case in audit_cases} == {'Q014'}
    assert audit_cases[0]['query_type'] == 'provenance'


def test_phase2_documents_exist_and_defer_implementation():
    expected = [
        'docs/CANONICAL_DATA_MODEL.md',
        'docs/CHUNKING_STRATEGY.md',
        'docs/RETRIEVAL_ARCHITECTURE.md',
        'docs/RAG_EVALUATION_PLAN.md',
        'docs/PHASE_2_ARCHITECTURE_DECISION.md',
    ]
    for relative_path in expected:
        content = (ROOT / relative_path).read_text(encoding='utf-8')
        assert len(content) > 200
    decision = (ROOT / 'docs/PHASE_2_ARCHITECTURE_DECISION.md').read_text(encoding='utf-8').lower()
    retrieval = (ROOT / 'docs/RETRIEVAL_ARCHITECTURE.md').read_text(encoding='utf-8').lower()
    assert 'implementation has not started' in decision
    assert 'no embeddings' in retrieval or 'embeddings' in retrieval
