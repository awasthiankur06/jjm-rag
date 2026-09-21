"""Resumable, PostgreSQL-only evaluation runner.

Each completed case is written immediately so an execution time limit cannot be
mistaken for a completed evaluation.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from jjm_rag.config import settings as _settings
from jjm_rag.persistence.database import get_database_session
from jjm_rag.production.evaluation_adapter import ProductionEvaluationAdapter, build_production_evaluation_adapter
from jjm_rag.retrieval.evaluate import (
    audit_evidence_available,
    expected_sources,
    hit_fraction,
    production_expected_sources,
    provenance_valid,
    sources_satisfy,
    unique_sources_at,
)


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def _evidence_dicts(items):
    return [item.__dict__ for item in items]


def _case_result(adapter: ProductionEvaluationAdapter, case: dict[str, Any], artifact_root: Path) -> dict[str, Any]:
    started = time.perf_counter()
    query = case["query"]
    routed = adapter.retrieve(query, top_k=10)
    route_filters = routed["route"].get("filters", {})
    exact = adapter.exact.search(query, top_k=10)
    lexical = adapter.store.lexical(query, 10)
    structured = adapter.structured.search(query, route_filters, top_k=10)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    expected = expected_sources(case)
    production_expected = production_expected_sources(case)
    audit_expected = {name for name in expected if name.startswith("artifacts/")}
    evidence = routed["evidence"]
    actual = {item["filename"] for item in evidence}
    exact_sources = {item.filename for item in exact}
    lexical_sources = {item.filename for item in lexical}
    structured_sources = {item.filename for item in structured}
    audit_hit = audit_evidence_available(case, artifact_root) and audit_expected <= exact_sources
    source_hit = (
        (not production_expected or (production_expected <= actual if case["requires_multiple_sources"] else bool(production_expected & actual)))
        and (not audit_expected or audit_hit)
    )
    expected_route = "EXACT" if case["query_type"] == "provenance" else case["query_type"].upper()
    route_hit = routed["route"]["query_type"] == expected_route
    expected_in_exact = sources_satisfy(case, production_expected, exact_sources) if case["requires_exact_match"] and not audit_expected else "NOT_APPLICABLE"
    expected_in_lexical = sources_satisfy(case, production_expected, lexical_sources) if production_expected else "NOT_APPLICABLE"
    expected_in_structured = sources_satisfy(case, production_expected, structured_sources) if case["requires_structured_query"] else "NOT_APPLICABLE"
    provenance_ok = (audit_hit if audit_expected else provenance_valid(evidence)) if case["requires_provenance"] else "NOT_APPLICABLE"
    reason = None
    if not source_hit:
        reason = "expected source absent from routed evidence"
    elif not route_hit:
        reason = "routing decision differs from evaluation expectation"
    elif provenance_ok is False:
        reason = "returned evidence lacks required provenance"
    return {
        "id": case["id"], "query": query, "query_type": case["query_type"],
        "expected_sources": sorted(expected), "expected_production_sources": sorted(production_expected),
        "requires_multiple_sources": case["requires_multiple_sources"],
        "routing": routed["route"], "route_pass": route_hit,
        "routed_evidence": evidence, "retrieved_document_ids": sorted({str(item.get("metadata", {}).get("document_id")) for item in evidence if item.get("metadata", {}).get("document_id")}),
        "retrieved_titles": sorted({str(item.get("metadata", {}).get("extracted_document_title") or item["filename"]) for item in evidence}),
        "exact_evidence": _evidence_dicts(exact), "lexical_evidence": _evidence_dicts(lexical), "structured_evidence": _evidence_dicts(structured),
        "source_pass": source_hit, "exact_pass": expected_in_exact, "lexical_pass": expected_in_lexical,
        "structured_pass": expected_in_structured, "provenance_pass": provenance_ok,
        "recall": {str(k): hit_fraction(production_expected, unique_sources_at(evidence, k)) if production_expected else "NOT_APPLICABLE" for k in (1, 5, 10)},
        "latency_ms": elapsed_ms, "pass_fail_reason": reason or "PASS",
    }


def _metrics(completed: list[dict[str, Any]], excluded_filename: str) -> dict[str, Any]:
    def rate(values):
        values = [value for value in values if isinstance(value, bool)]
        return sum(values) / len(values) if values else "NOT_EVALUABLE"
    recall = {}
    for key in ("1", "5", "10"):
        values = [item["recall"][key] for item in completed if isinstance(item["recall"][key], float)]
        recall[f"recall_at_{key}"] = sum(values) / len(values) if values else "NOT_EVALUABLE"
    exclusion_safe = all(excluded_filename not in {item["filename"] for item in case["routed_evidence"]} for case in completed)
    cross = [case["source_pass"] for case in completed if case["query_type"] == "cross_document"]
    return {
        "completed_cases": len(completed), "routing_accuracy": rate([case["route_pass"] for case in completed]),
        "source_identification_accuracy": rate([case["source_pass"] for case in completed]),
        "exact_retrieval_accuracy": rate([case["exact_pass"] for case in completed]),
        "lexical_retrieval_accuracy": rate([case["lexical_pass"] for case in completed]),
        "structured_retrieval_accuracy": rate([case["structured_pass"] for case in completed]),
        "provenance_accuracy": rate([case["provenance_pass"] for case in completed]),
        "cross_document_accuracy": sum(cross) / len(cross) if cross else "NOT_EVALUABLE",
        "numeric_aggregation_accuracy": "NOT_EVALUABLE: no verified answer-level numeric ground truth in this contract",
        "excluded_source_safety": exclusion_safe, "regression_count": "NOT_EVALUABLE until a complete post-rebuild run is compared to a compatible current baseline", **recall,
    }


def run(cases_path: Path, output_path: Path, start: int, batch_size: int, *, with_semantic: bool = False) -> dict[str, Any]:
    cases = _read(cases_path)["cases"]
    mode = "postgresql_with_validated_qdrant" if with_semantic else "postgresql_deterministic_only"
    state = _read(output_path) if output_path.exists() else {"artifact_type": "resumable_postgresql_evaluation", "mode": mode, "cases": {}}
    completed = state["cases"]
    adapter = build_production_evaluation_adapter({}) if with_semantic else ProductionEvaluationAdapter(get_database_session(), None)
    try:
        for case in cases[start:start + batch_size]:
            if case["id"] in completed:
                continue
            completed[case["id"]] = _case_result(adapter, case, output_path.parent.parent)
            state["cases"] = completed
            state["metrics_if_complete"] = _metrics(list(completed.values()), "Status of Pipe Water Supply in School (2).xls")
            state["case_count_expected"] = len(cases)
            state["complete"] = len(completed) == len(cases)
            _write(output_path, state)
    finally:
        adapter.session.close()
    return state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=Path("artifacts/query_evaluation_cases.json"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/post_rebuild_postgres_evaluation.json"))
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--with-semantic", action="store_true", help="use the configured canonical-validated Qdrant collection")
    args = parser.parse_args()
    state = run(args.cases, args.output, args.start, args.batch_size, with_semantic=args.with_semantic)
    print(json.dumps({"completed": len(state["cases"]), "expected": state["case_count_expected"], "complete": state["complete"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
