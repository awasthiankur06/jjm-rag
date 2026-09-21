import json
from pathlib import Path

from jjm_rag.production.evaluation_adapter import ProductionEvaluationAdapter
from jjm_rag.retrieval.evaluate import evaluate_cases


class Store:
    def exact(self, query, limit): return []
    def lexical(self, query, limit): return []
    def structured(self, query, filters, limit): return []


class Semantic:
    def search(self, query, filters, limit): return []


def test_production_adapter_preserves_evaluator_contract_for_existing_cases():
    root = Path(__file__).resolve().parents[1]
    artifact = json.loads((root / "artifacts" / "prototype_manifest.json").read_text(encoding="utf-8"))
    cases = json.loads((root / "artifacts" / "query_evaluation_cases.json").read_text(encoding="utf-8"))["cases"][:4]
    adapter = ProductionEvaluationAdapter(None, Semantic(), evidence_store=Store())
    result = evaluate_cases(artifact, cases, root, retriever_factory=lambda _: adapter)
    assert result["case_count"] == 4
    assert result["executed_case_count"] == 4


def test_production_adapter_degrades_without_a_semantic_provider():
    adapter = ProductionEvaluationAdapter(None, None, evidence_store=Store())
    assert adapter.semantic.search("policy guidance", top_k=10) == []
