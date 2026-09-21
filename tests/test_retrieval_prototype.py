import json
from pathlib import Path

from jjm_rag.retrieval.prototype import EXCLUDED_FILENAME, PrototypeRetriever


ROOT = Path('d:/jjm-rag')


def prototype():
    return PrototypeRetriever(json.loads((ROOT / 'artifacts/prototype_manifest.json').read_text(encoding='utf-8')))


def test_excluded_source_never_enters_prototype_index():
    artifact = json.loads((ROOT / 'artifacts/prototype_manifest.json').read_text(encoding='utf-8'))
    assert EXCLUDED_FILENAME not in {document['filename'] for document in artifact['documents']}
    assert EXCLUDED_FILENAME not in {row['filename'] for row in artifact['rows']}
    assert EXCLUDED_FILENAME not in {page['filename'] for page in artifact['pages']}
    excluded = next(item for item in artifact['excluded_sources'] if item['filename'] == EXCLUDED_FILENAME)
    assert excluded['indexed'] is False


def test_exact_retrieval_finds_format_and_report_identity():
    results = prototype().exact.search('Which report contains the CS1(A) coverage fields?', top_k=3)
    assert results
    assert results[0].filename == 'CS1 A. Coverage.xls'
    assert results[0].retrieval_method == 'exact'


def test_structured_filter_and_aggregation_preserve_rows():
    retriever = prototype().structured
    rows = retriever.rows({'filename': 'District wise number of Rural Population as on (01 (1).xls', 'state': 'Maharashtra'})
    assert rows
    ahmednagar = [row for row in rows if row['values'][1] == 'Ahmednagar']
    assert len(ahmednagar) == 1
    assert retriever.numeric_value(ahmednagar[0], 'TOTAL') == 3947868
    assert retriever.aggregate(ahmednagar, 'TOTAL') == 3947868
    assert retriever.rank(rows[:3], 'TOTAL')[0]['values'][1] in {'Ahmednagar', 'Akola', 'Amravati'}


def test_provenance_and_ocr_metadata_survive_retrieval():
    results = prototype().semantic.search('Har Ghar Jal implementation guidance', top_k=10)
    assert results
    ocr_results = [result for result in results if result.filename == 'Operational-Guidelines-JJM-2.pdf']
    assert ocr_results
    assert all('page' in result.location for result in ocr_results)
    assert all(result.metadata['ocr'] is True for result in ocr_results)


def test_metadata_filtering_and_hybrid_retrieval():
    retriever = prototype()
    rows = retriever.structured.rows({'state': 'Assam'})
    assert rows
    assert all('Assam' in row['metadata'].get('parameter_text', '') or 'Assam' in row['values'] for row in rows)
    hybrid = retriever.retrieve('What does the FUA3 report say about approval of geotagged water sources?', top_k=10)
    assert hybrid['route']['query_type'] == 'HYBRID'
    assert hybrid['evidence']
    assert {'exact', 'semantic'} <= set(hybrid['strategies'])


def test_router_and_insufficient_evidence():
    retriever = prototype()
    assert retriever.router.route('What guidance applies to operation and maintenance?').query_type == 'POLICY'
    assert retriever.router.route('Compare Assam and Maharashtra reports.').query_type == 'CROSS_DOCUMENT'
    unknown = retriever.retrieve('unrelated fabricated topic with no corpus evidence', top_k=5)
    assert unknown['insufficient_evidence'] is True


def test_multi_state_cross_document_requires_entity_specific_evidence():
    retriever = prototype()
    query = 'Compare rural population totals for Assam, Maharashtra, Tamil Nadu, and Uttarakhand on 01/04/2026.'
    result = retriever.retrieve(query, top_k=10)
    filenames = [item['filename'] for item in result['evidence']]
    assert any('AssamDistrict wise number of Rural Population as on (01.xls' in filename for filename in filenames)
    assert any('District wise number of Rural Population as on (01 (1).xls' in filename for filename in filenames)
    assert any('District wise number of Rural Population as on (01 (2).xls' in filename for filename in filenames)
    assert any('District wise number of Rural Population as on (01.xls' in filename for filename in filenames)


def test_exact_state_filters_are_applied_to_pm4_state_lookup():
    retriever = prototype()
    query = 'Which PM4 files cover Maharashtra, Tamil Nadu, Punjab, and Andaman & Nicobar Islands?'
    result = retriever.retrieve(query, top_k=10)
    filenames = [item['filename'] for item in result['evidence']]
    assert 'Progress tracker of verification of schemes.xls' in filenames
    assert 'Progress tracker of verification of schemes (1).xls' in filenames
    assert 'Progress tracker of verification of schemes (2).xls' in filenames
    assert 'Progress tracker of verification of schemes (3).xls' in filenames
    assert not any(filename.startswith('CS1') for filename in filenames)


def test_policy_and_numeric_subtasks_are_decomposed_and_separated():
    retriever = prototype()
    query = 'Which source is authoritative for a policy definition, and which source is authoritative for a district numeric value?'
    result = retriever.retrieve(query, top_k=20)
    assert 'decomposition' in result
    assert len(result['decomposition']) >= 2
    policy_hits = [subtask for subtask in result['decomposition'] if subtask['query_type'] == 'POLICY']
    numeric_hits = [subtask for subtask in result['decomposition'] if subtask['query_type'] == 'STRUCTURED']
    assert policy_hits
    assert numeric_hits
    policy_sources = {item['filename'] for item in policy_hits[0]['evidence']}
    numeric_sources = {item['filename'] for item in numeric_hits[0]['evidence']}
    assert policy_sources & numeric_sources == set()


def test_excluded_source_queries_return_audit_provenance_without_indexing_source():
    result = prototype().retrieve(
        'What is the status of the Maharashtra school water-supply report artifact numbered (2)?',
        top_k=10,
    )
    sources = {item['filename'] for item in result['evidence']}
    assert 'artifacts/status_pipe_water_forensic.json' in sources
    assert EXCLUDED_FILENAME not in sources
    audit = next(item for item in result['evidence'] if item['filename'].startswith('artifacts/'))
    assert audit['location']['audit'] is True


def test_version_queries_expand_family_without_suffix_ordering():
    result = prototype().retrieve(
        'Are the PM4 files duplicate exports, structural variants, or different state snapshots?',
        top_k=10,
    )
    sources = {item['filename'] for item in result['evidence']}
    assert sources == {
        'Progress tracker of verification of schemes.xls',
        'Progress tracker of verification of schemes (1).xls',
        'Progress tracker of verification of schemes (2).xls',
        'Progress tracker of verification of schemes (3).xls',
    }
    assert all(
        item['metadata']['version_evidence']['ordering_evidence'] == 'INSUFFICIENT_VERSION_EVIDENCE'
        for item in result['evidence']
    )


def test_cross_document_alignment_preserves_state_and_report_dimensions():
    result = prototype().retrieve(
        'Compare beneficiary verification records for Assam, Maharashtra, and Tamil Nadu.',
        top_k=10,
    )
    aligned = [item for item in result['evidence'] if 'alignment' in item['metadata']]
    assert {item['metadata']['alignment']['entity'] for item in aligned} == {
        'Assam', 'Maharashtra', 'Tamil Nadu'
    }
    assert {item['metadata']['format_code'] for item in aligned} == {'J6'}
    assert {item['metadata']['date'] for item in aligned} == {'30/08/2026'}
