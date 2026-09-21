from __future__ import annotations

import hashlib
import json
import sys
import traceback
from pathlib import Path

from jjm_rag.retrieval.evaluate import run_evaluation
from jjm_rag.retrieval.prototype import PrototypeRetriever

root = Path(r'd:\jjm-rag')
baseline_path = root / 'artifacts' / 'retrieval_evaluation_baseline.json'
dataset_path = root / 'artifacts' / 'query_evaluation_cases.json'
manifest_path = root / 'artifacts' / 'prototype_manifest.json'
out_path = root / 'artifacts' / 'retrieval_evaluation_results.json'

print('ROOT', root)
print('PY', sys.executable)
print('VER', sys.version)

if not baseline_path.exists():
    raise FileNotFoundError(f'Baseline missing: {baseline_path}')

baseline = json.loads(baseline_path.read_text(encoding='utf-8'))
print('BASELINE_CASE_COUNT', baseline.get('case_count'))
print('BASELINE_EXECUTED', baseline.get('executed_case_count'))
print('BASELINE_ROUTING', baseline.get('metrics', {}).get('routing_accuracy'))

if not dataset_path.exists():
    raise FileNotFoundError(f'Dataset missing: {dataset_path}')

dataset = json.loads(dataset_path.read_text(encoding='utf-8'))
cases = dataset.get('cases', [])
print('DATASET_CASE_COUNT', len(cases))
print('CASE_IDS', [c.get('id') for c in cases[:5]], '...', [c.get('id') for c in cases[-5:]])
if len(cases) != 40:
    raise ValueError(f'Expected 40 cases, got {len(cases)}')
if len({c.get('id') for c in cases}) != 40:
    raise ValueError('Duplicate or non-unique case IDs present')

if not manifest_path.exists():
    raise FileNotFoundError(f'Manifest missing: {manifest_path}')
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
print('MANIFEST_LOADED', 'artifact_type' in manifest, manifest.get('artifact_type'))
retriever = PrototypeRetriever(manifest)
print('RETRIEVER_OK', type(retriever).__name__)
case = cases[0]
res = retriever.retrieve(case['query'], top_k=5)
print('CASE0_ROUTE', res.get('route', {}).get('query_type'))
print('CASE0_EVIDENCE_LEN', len(res.get('evidence', [])))

res_runtime = run_evaluation(manifest_path, dataset_path, manifest_path, out_path)
print('RUNTIME_CASE_COUNT', res_runtime.get('case_count'))
print('RUNTIME_EXECUTED', res_runtime.get('executed_case_count'))
print('RUNTIME_ROUTING', res_runtime.get('metrics', {}).get('routing_accuracy'))
print('RUNTIME_FAILURES', res_runtime.get('failure_categories'))

persisted = json.loads(out_path.read_text(encoding='utf-8'))
print('ARTIFACT_CASE_COUNT', persisted.get('case_count'))
print('ARTIFACT_EXECUTED', persisted.get('executed_case_count'))
print('ARTIFACT_ROUTING', persisted.get('metrics', {}).get('routing_accuracy'))
print('EQUAL_CASE_COUNT', res_runtime.get('case_count') == persisted.get('case_count'))
print('EQUAL_EXECUTED', res_runtime.get('executed_case_count') == persisted.get('executed_case_count'))
print('EQUAL_METRICS', res_runtime.get('metrics') == persisted.get('metrics'))
print('EQUAL_FAILURES', res_runtime.get('failure_categories') == persisted.get('failure_categories'))

# write proof artifact
sha256 = hashlib.sha256(out_path.read_bytes()).hexdigest()
summary = {
    'evaluation_timestamp': __import__('datetime').datetime.utcnow().isoformat() + 'Z',
    'project_root': str(root),
    'python_executable': str(Path(sys.executable)),
    'python_version': sys.version,
    'evaluator_module': 'jjm_rag.retrieval.evaluate.run_evaluation',
    'evaluation_dataset_sha256': hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
    'prototype_manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    'output_artifact_sha256': sha256,
    'case_count': persisted.get('case_count'),
    'executed_case_count': persisted.get('executed_case_count'),
    'status_counts': {
        'PASS': sum(1 for case in persisted.get('cases', []) if case.get('expected_evidence_retrieved') is True),
        'FAIL': sum(1 for case in persisted.get('cases', []) if case.get('expected_evidence_retrieved') is False),
        'NOT_EVALUABLE': sum(1 for case in persisted.get('cases', []) if case.get('expected_evidence_retrieved') == 'NOT_EVALUABLE'),
    },
    'metrics': persisted.get('metrics'),
    'failure_categories': persisted.get('failure_categories'),
}
(root / 'artifacts' / 'fresh_eval_run.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
print('FRESH_PROOF_SAVED', root / 'artifacts' / 'fresh_eval_run.json')
