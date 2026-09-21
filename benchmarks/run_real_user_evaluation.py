"""Run realistic JJM questions through the existing FastAPI/RagService boundary."""
from __future__ import annotations

import json
import re
import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from jjm_rag.production.api import create_app
from jjm_rag.production.cli import build_service

ARTIFACT = ROOT / "artifacts" / "real_user_question_evaluation.json"
OUTPUT = ROOT / "artifacts" / "real_user_question_evaluation_results.json"
REPORT = ROOT / "docs" / "REAL_USER_QUESTION_EVALUATION.md"
CHECKPOINT = ROOT / "tmp" / "real_user_question_evaluation_checkpoint.json"


def source_hit(case: dict[str, Any], response: dict[str, Any]) -> bool:
    expected = set(case["expected_sources"])
    actual = {item.get("filename") for item in response.get("evidence", [])}
    if not expected:
        return not response.get("evidence") or response.get("confidence", {}).get("grounded") is False
    if case["category"] == "cross_document":
        return expected <= actual
    return bool(expected & actual)


def route_expected(case: dict[str, Any]) -> set[str]:
    return {
        "policy_guideline": {"semantic", "hybrid"},
        "exact_numeric": {"structured", "hybrid"},
        "state_level": {"structured", "hybrid"},
        "district_level": {"structured", "hybrid"},
        "report_fact": {"exact", "structured", "semantic", "hybrid"},
        "comparison": {"structured", "hybrid"},
        "aggregation": {"structured", "hybrid"},
        "cross_document": {"hybrid", "structured", "semantic", "exact"},
        "reporting_period": {"structured", "exact", "hybrid", "semantic"},
        "unsupported_abstention": {"structured", "exact", "semantic", "hybrid"},
    }.get(case["category"], {"exact", "structured", "semantic", "hybrid"})


def numeric_accuracy(case: dict[str, Any], response: dict[str, Any]) -> bool | str:
    expected = case.get("expected_values", [])
    if not expected or case.get("ground_truth_status") == "derive_from_structured_record":
        return "NOT_EVALUABLE"
    typed_values = [fact.get("metadata", {}).get("value_numeric") for fact in response.get("structured_facts", [])]
    if typed_values and all(any(str(value) == str(observed) for observed in typed_values) for value in expected):
        return True
    answer = response.get("answer", "")
    normalized = re.sub(r",", "", answer)
    return all(re.search(rf"(?<!\d){re.escape(str(value))}(?!\d)", normalized) for value in expected)


def calculation_accuracy(case: dict[str, Any], response: dict[str, Any]) -> bool | str:
    if not case.get("calculation_required"):
        return "NOT_APPLICABLE"
    result = case.get("expected_calculation", {}).get("result")
    if not isinstance(result, (int, float)):
        return "NOT_EVALUABLE"
    calculation = response.get("calculation") or {}
    if calculation:
        expected_operation = case.get("expected_calculation", {}).get("operation")
        expected_unit = case.get("expected_calculation", {}).get("unit")
        expected_operands = case.get("expected_calculation", {}).get("operand_values")
        operands = calculation.get("inputs", [])
        operand_values = [item.get("value") for item in operands]
        operation_ok = not expected_operation or calculation.get("operation") == expected_operation or ({calculation.get("operation"), expected_operation} <= {"compare", "difference"})
        return calculation.get("result") == result and operation_ok and (not expected_unit or all(item.get("unit") == expected_unit for item in operands)) and (not expected_operands or all(value in operand_values for value in expected_operands)) and all(item.get("provenance_id") for item in operands)
    normalized = re.sub(r",", "", response.get("answer", ""))
    return bool(re.search(rf"(?<!\d){re.escape(str(result))}(?!\d)", normalized))


def failure_category(case: dict[str, Any], response: dict[str, Any], source_ok: bool, route_ok: bool) -> str | None:
    confidence = response.get("confidence", {})
    if case["expected_abstention"]:
        return None if not confidence.get("grounded") else "abstention_failure"
    if not route_ok:
        return "wrong_routing"
    if not source_ok:
        category = case["category"]
        return {"policy_guideline": "semantic_retrieval_failure", "exact_numeric": "structured_retrieval_failure", "state_level": "geography_filtering_failure", "district_level": "geography_filtering_failure", "reporting_period": "reporting_period_failure", "cross_document": "cross_document_alignment_failure"}.get(category, "retrieval_failure")
    if confidence.get("grounded") is False:
        return "grounding_failure"
    if case.get("calculation_required") and calculation_accuracy(case, response) is False:
        return "calculation_failure"
    if numeric_accuracy(case, response) is False:
        return "numeric_extraction_failure"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run realistic JJM questions through the production API boundary")
    parser.add_argument("--max-cases", type=int, help="Process at most this many new cases")
    parser.add_argument("--no-resume", action="store_true", help="Ignore the incremental checkpoint")
    args = parser.parse_args()
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    client = TestClient(create_app(build_service()))
    results: list[dict[str, Any]] = []
    completed_ids: set[str] = set()
    if not args.no_resume and CHECKPOINT.exists():
        try:
            saved = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
            results = saved.get("cases", [])
            completed_ids = {item["question_id"] for item in results}
        except (OSError, json.JSONDecodeError, KeyError, TypeError):
            results = []
            completed_ids = set()
    new_cases = 0
    for case in artifact["cases"]:
        if case["question_id"] in completed_ids:
            continue
        if args.max_cases is not None and new_cases >= args.max_cases:
            break
        api_response = client.post("/api/v1/query", json={"query": case["question"]})
        response = api_response.json() if api_response.headers.get("content-type", "").startswith("application/json") else {"answer": api_response.text}
        actual_route = response.get("retrieval", {}).get("route")
        source_ok = source_hit(case, response)
        route_ok = actual_route in route_expected(case)
        grounded = response.get("confidence", {}).get("grounded") is True
        abstention_ok = (not grounded) if case["expected_abstention"] else "NOT_APPLICABLE"
        citations = response.get("citations", [])
        citation_sources_ok = all(item.get("filename") in {e.get("filename") for e in response.get("evidence", [])} for item in citations)
        provenance_resolved = all(item.get("content_unit_id") and item.get("filename") for item in citations)
        result = {
            "question_id": case["question_id"], "question": case["question"], "category": case["category"],
            "http_status": api_response.status_code, "route": actual_route, "channels": response.get("retrieval", {}).get("channels", []),
            "retrieved_filenames": sorted({item.get("filename") for item in response.get("evidence", [])}),
            "evidence_count": response.get("confidence", {}).get("evidence_count", 0), "answer": response.get("answer", ""),
            "citations": citations, "grounding": response.get("confidence", {}), "warnings": response.get("warnings", []),
            "retrieval_correct": source_ok, "routing_correct": route_ok, "numeric_correct": numeric_accuracy(case, response),
            "calculation_correct": calculation_accuracy(case, response), "citation_sources_correct": citation_sources_ok,
            "answer_type": response.get("answer_type"), "structured_facts": response.get("structured_facts", []), "calculation": response.get("calculation"),
            "citation_resolution_correct": provenance_resolved, "abstention_correct": abstention_ok,
            "failure_category": failure_category(case, response, source_ok, route_ok),
        }
        results.append(result)
        new_cases += 1
        CHECKPOINT.write_text(json.dumps({"artifact_type": "real_user_question_evaluation_checkpoint", "question_count": len(results), "cases": results}, indent=2, ensure_ascii=False), encoding="utf-8")

    def rate(values: list[Any], predicate) -> float | str:
        applicable = [value for value in values if value != "NOT_EVALUABLE" and value != "NOT_APPLICABLE"]
        return sum(predicate(value) for value in applicable) / len(applicable) if applicable else "NOT_EVALUABLE"

    metrics = {
        "routing_accuracy": rate([item["routing_correct"] for item in results], bool),
        "recall_at_1": "NOT_EVALUABLE_FROM_RESPONSE_ONLY",
        "recall_at_3": "NOT_EVALUABLE_FROM_RESPONSE_ONLY",
        "recall_at_5": "NOT_EVALUABLE_FROM_RESPONSE_ONLY",
        "recall_at_10": rate([item["retrieval_correct"] for item in results], bool),
        "grounded_answer_rate": sum(item["grounding"].get("grounded") is True for item in results) / len(results),
        "correct_answer_rate": "NOT_EVALUABLE_FOR_QUALITATIVE_CASES",
        "numeric_accuracy": rate([item["numeric_correct"] for item in results], bool),
        "geographic_accuracy": "NOT_EVALUABLE_WITHOUT_ANSWER_LEVEL_GEOGRAPHY_JUDGER",
        "citation_provenance_accuracy": rate([item["citation_resolution_correct"] for item in results], bool),
        "citation_source_accuracy": rate([item["citation_sources_correct"] for item in results], bool),
        "cross_document_success": rate([item["retrieval_correct"] for item in results if item["category"] == "cross_document"], bool),
        "abstention_correctness": rate([item["abstention_correct"] for item in results], bool),
        "calculation_retrieval_correct": rate([item["retrieval_correct"] for item in results if artifact_case(question_id=item["question_id"], artifact=artifact).get("calculation_required")], bool),
        "calculation_correct": rate([item["calculation_correct"] for item in results], bool),
        "calculation_final_answer_correct": "NOT_EVALUABLE_WHERE_EXPECTED_RESULT_IS_DERIVED",
    }
    output = {"artifact_type": "real_user_question_evaluation_results", "question_count": len(results), "completed": len(results) == len(artifact["cases"]), "category_distribution": dict(Counter(item["category"] for item in results)), "metrics": metrics, "failure_categories": dict(Counter(item["failure_category"] for item in results if item["failure_category"])), "cases": results, "execution": {"boundary": "FastAPI TestClient -> /api/v1/query -> existing RagService", "reindexed": False, "protected_artifacts_modified": False}}
    if results:
        OUTPUT.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    report = "# Real User Question Evaluation\n\n" + f"Executed **{len(results)}** realistic JJM questions through the existing FastAPI `/api/v1/query` and `RagService` path.\n\n" + "## Distribution\n\n" + "\n".join(f"- {key}: {value}" for key, value in output["category_distribution"].items()) + "\n\n## Metrics\n\n" + "\n".join(f"- {key}: {value}" for key, value in metrics.items()) + "\n\n## Failure categories\n\n" + ("\n".join(f"- {key}: {value}" for key, value in output["failure_categories"].items()) or "- None recorded") + "\n\n## Interpretation\n\nThis is a measured production-path baseline. Numeric and calculation rates are intentionally marked unevaluable where answer-level ground truth was not independently derived from structured records. The current API returns retrieved evidence and Grok output but does not expose a deterministic structured calculation service; that is the main next engineering gap.\n"
    REPORT.write_text(report, encoding="utf-8")
    print(json.dumps({"question_count": len(results), "completed": output["completed"], "new_cases": new_cases, "checkpoint": str(CHECKPOINT), "metrics": metrics, "failure_categories": output["failure_categories"]}, indent=2))
    return 0


def artifact_case(question_id: str, artifact: dict[str, Any]) -> dict[str, Any]:
    return next(case for case in artifact["cases"] if case["question_id"] == question_id)


if __name__ == "__main__":
    raise SystemExit(main())
